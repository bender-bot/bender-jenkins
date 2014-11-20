import pickle
import re
import threading

from jenkins import Jenkins
from requests.exceptions import HTTPError

from bender.decorators import respond, script_initialize, script_shutdown
from concurrent.futures.thread import ThreadPoolExecutor


class BenderJenkinsScript(object):
    '''
    Script that provides communication with Jenkins CI.

    It gives you support to obtain status of jobs through a given regular
    expression and provide a feedback whenever the status is updated.
    '''

    # Memory name that will be used at Bender's brain to store/retrieve
    # information related to this script .
    _MEMORY_NAME = 'jenkins'

    def _create_server(self, brain):
        '''
        :param :class:`.Brain` brain:
            Placeholder where `url` information will be retrieved.

        :rtype: :class:`.Jenkins` | None
        :returns:
            Instance that communicates with Jenkins service.
        '''
        url = brain[self._MEMORY_NAME].get('url')
        if url:
            username = brain[self._MEMORY_NAME].get('username')
            password = brain[self._MEMORY_NAME].get('password')
            return Jenkins(url, username, password)

    def _update_interval(self, brain):
        '''
        :param :class:`.Brain` brain:
            Placeholder where `update_interval` information will be retrieved.

        :rtype: int
        :returns:
            Interval (in seconds) between each update event.
        '''
        return int(brain[self._MEMORY_NAME].get('update_interval', 60))

    def _notify(self, brain, stop_event):
        '''
        Notifies about time stamp changes related to all jobs that matches
        registered job patterns.

        That means that even a job status keeps the same but this is a result of
        a new build, a notification will be triggered.

        :param :class:`.Brain` brain:
            Placeholder where information related to notification event will be
            retrieved.

        :param :class:`threading.Event` stop_event:
            Event that will be used to stop notification event.
        '''

        def do_notify(job, latest_build_state):

            try:
                # Retrieving last build info.
                build = job.last_build
                current_state = build.number, build.info['result'] or u'BUILDING'
            except HTTPError:
                # There are no builds available.
                current_state = -1, None

            # Current job was never cached or built there is nothing to compare with.
            if latest_build_state is None:
                latest_build_state = current_state

            # Still the same build.
            if current_state == latest_build_state:
                return latest_build_state

            # Notify about new build status.
            for job_pattern, notifiers in self._jenkins_notifiers.items():

                if not re.match(job_pattern, job.name):
                    continue

                for msg in notifiers.values():
                    msg.reply(' [%s] %s\n        %s' % (current_state[1], job.name, build.info['url']))

            return current_state

        latest_build_states = {}
        class on_done(object):

            def __init__(self, job_name):
                self.job_name = job_name

            def __call__(self, future):
                latest_build_states[self.job_name] = future.result()
        
        pool = ThreadPoolExecutor(max_workers=16)
        while True:
            server = self._create_server(brain)
            if server is not None:
                for job in server.jobs:
                    result = pool.submit(do_notify, job, latest_build_states.get(job.name))
                    result.add_done_callback(on_done(job.name))

            stop_event.wait(self._update_interval(brain))
            if stop_event.is_set():
                return

    @script_initialize
    def initialize(self, brain):
        memory = brain.setdefault(self._MEMORY_NAME, {})

        self._jenkins_notifiers = {}

        job_patterns = memory.setdefault('job_patterns', {})
        for job_pattern, messages in job_patterns.items():
            for message in messages.values():
                loaded_message = pickle.loads(message)
                notifiers = self._jenkins_notifiers.setdefault(job_pattern, {})
                notifiers[loaded_message.get_sender()] = loaded_message

        self._jenkins_notifier_stop_loop = threading.Event()

        self._jenkins_notifier_thread = threading.Thread(target=self._notify, args=(brain, self._jenkins_notifier_stop_loop))
        self._jenkins_notifier_thread.start()

    @script_shutdown
    def shutdown(self):
        self._jenkins_notifier_stop_loop.set()

    @respond(r'jenkins get url')
    def get_url(self, brain, msg):
        '''
        Inform URL currently set for Jenkins service.

        > jenkins get url
        URL: http://localhost/

        > jenkins get url
        There is no such information available.
        '''
        result = brain[self._MEMORY_NAME].get('url')
        if result is not None:
            result = 'URL: %s' % result
        else:
            result = 'There is no such information available.'
        msg.reply(result)

    @respond(r'jenkins get update interval')
    def get_update_interval(self, brain, msg):
        '''
        Inform interval currently set to search for Jenkins updates.

        > jenkins get update interval
        Update interval: 60 seconds

        > jenkins get update interval
        There is no such information available.
        '''
        result = brain[self._MEMORY_NAME].get('update_interval')
        if result is not None:
            result = 'Update interval: %d seconds' % int(result)
        else:
            result = 'There is no such information available.'
        msg.reply(result)

    @respond('jenkins job status (.*)')
    def job_status(self, brain, msg, match):
        '''
        Request current status for given job pattern.

        Pattern may be a regular expression.

        > jenkins job status gui-master-.*
        This might take a while. Please wait...
        [RUNNING] gui-master-win32
        [NOT BUILT] gui-master-win64
        [FAILED] gui-master-redhat64
        '''
        server = self._create_server(brain)
        if server is None:
            msg.reply('There is no Jenkins server set.')

        msg.reply('This might take a while. Please wait...')
        job_pattern = match.group(1).strip()

        result = []
        for job in server.jobs:

            job_name = job.name
            if not re.match(job_pattern, job_name, re.IGNORECASE | re.DOTALL):
                continue

            try:
                build = job.last_build
            except HTTPError:
                # There are no builds available.
                result.append('[NOT BUILT] %s' % (job_name))
                continue

            if build.building:
                result.append('[RUNNING] %s' % job_name)
            else:
                info = build.info
                result.append('[%s] %s\n        %s' % (info['result'], job_name, info['url']))

        if result:
            result_as_str = 'Current job status:\n'
            for i in result:
                result_as_str += ' - %s\n' % i
            msg.reply(result_as_str)
        else:
            msg.reply('I found no jobs for you... loser!')

    @respond('jenkins notify me (.*)')
    def notify_me(self, brain, msg, match):
        '''
        Register yourself to be notified about job status updates.

        It is necessary to provide a job pattern (which may be a regular
        expression).

        > jenkins notify me gui-master-.*
        You were added to gui-master-.*

        # About one hour has passed...
        [PASSED] gui-master-win32
        # Another one hour...
        [PASSED] gui-master-win32
        # And one hour more...
        [FAILED] gui-master-win32
        '''
        job_patterns = brain[self._MEMORY_NAME].setdefault('job_patterns', {})
        job_pattern = match.group(1).strip()
        messages = job_patterns.setdefault(job_pattern, {})

        sender = msg.get_sender()
        if sender not in messages:
            messages[sender] = pickle.dumps(msg)
            notifiers = self._jenkins_notifiers.setdefault(job_pattern, {})
            notifiers[sender] = msg
            msg.reply('You were added to %s' % job_pattern)
        else:
            msg.reply('Again? You are already there!')

    @respond('jenkins remove me (.*)')
    def remove_me(self, brain, msg, match):
        '''
        Remove yourself from a notification.

        It is necessary to provide a job pattern (which may be a regular
        expression).

        > jenkins remove me gui-master-.*
        You've been removed from gui-master-.*
        '''
        job_patterns = brain[self._MEMORY_NAME].setdefault('job_patterns', {})
        job_pattern = match.group(1).strip()
        messages = job_patterns.setdefault(job_pattern, {})

        sender = msg.get_sender()
        if sender in messages:
            notifiers = self._jenkins_notifiers.setdefault(job_pattern, {})
            del notifiers[sender]
            del messages[sender]
            msg.reply('You\'ve been removed from %s.' % job_pattern)
        else:
            msg.reply('Well, if you\'ve been there once, not anymore... loser!')

        if not messages:
            del job_patterns[job_pattern]

    @respond('jenkins show notifications')
    def show_notifications(self, brain, msg, match):
        '''
        Shows you all notifications you are currently registered.
        '''
        job_patterns = brain[self._MEMORY_NAME].setdefault('job_patterns', {})
        sender = msg.get_sender()

        result = []
        for job_pattern, messages in job_patterns.items():
            if sender in messages:
                result.append(job_pattern)

        if not result:
            msg.reply('I found no jobs for you :(')
        else:
            result_as_str = 'You are receiving notifications of following job patterns:\n'
            for i in result:
                result_as_str += ' - %s\n' % i
            msg.reply(result_as_str)
