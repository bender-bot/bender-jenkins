from bender.decorators import respond
from jenkinsapi.jenkins import Jenkins
import re


#===================================================================================================
# JenkinsBenderScript
#===================================================================================================
class JenkinsBenderScript(object):

    def initialize(self, brain):
        self._load_notifications()


    def _create_server(self, brain, msg):
        if 'jenkins_url' not in brain:
            msg.reply('Setup Jenkins URL before.')
            return
        return Jenkins(brain['jenkins_url'])
    
    
    def _username(self, brain, msg):
        sender = msg.get_sender()
        usernames = brain.setdefault('jenkins_usernames', {})
        username = usernames.get(sender)
        if not username:
            msg.reply('Setup your Jenkins username before.')
            return
        return username


    # Notifiers ------------------------------------------------------------------------------------
    def _build_status(self, brain, msg):

        while True:
            server = self._create_server(brain, msg)
            job_patterns = brain.setdefault('jenkins_job_patterns', {})

            # Checking for new builds.
            for job_name in server.iterkeys():

                for job_pattern, usernames in job_patterns.iteritems():

                    # Ignoring jobs that did not match to current job pattern.
                    if not re.match(job_pattern, job_name):
                        continue

                    self._check_for_new_build(job_name, server, usernames)

            time.sleep(update_interval)


    def set_update_interval(self):
        pass


    # URL ------------------------------------------------------------------------------------------
    @respond('set jenkins url (.*)')
    def set_url(self, brain, msg, match):
        brain['jenkins_url'] = url = match.group(1)
        msg.reply('%s was added as Jenkins URL' % url)


    @respond('get jenkins url')
    def get_url(self, brain, msg, match):
        msg.reply(brain.get('jenkins_url', 'There is no such information available.'))


    # Username -------------------------------------------------------------------------------------
    @respond('set jenkins username (.*)')
    def set_username(self, brain, msg, match):
        sender = msg.get_sender()
        usernames = brain.setdefault('jenkins_usernames', {})
        usernames[sender] = username = match.group(1)
        msg.reply('%s was added as your Jenkins username' % username)


    @respond('get jenkins username')
    def get_username(self, brain, msg, match):
        usernames = brain.setdefault('jenkins_usernames', {})
        msg.reply(usernames.get(msg.get_sender(), 'There is no such information available.'))


    @respond('hey')
    def hello(self, brain, msg, match):
        msg.reply(self.__class__.__name__ + ' is ON!')


    @respond('help')
    def help(self, brain, msg, match):
        msg.reply('Jenkins help')


    @respond('.*status.* (.*)')
    @respond('.*status.* (.*)[\.!?]^\*')
    @respond('.*status.* (.*),')
    def job_status(self, brain, msg, match):

        jenkins = self._create_server(brain, msg)
        if not jenkins:
            return

        msg.reply('This might take a while. Please wait...')
        job_pattern = match.group(1)

        result = []
        for job_name in jenkins.iterkeys():

            if not re.match(job_pattern, job_name, re.IGNORECASE | re.DOTALL):
                continue

            job = jenkins[job_name]
            if job.is_running():
                result.append('[RUNNING] %s' % job_name)

            else:
                build = job.get_last_build_or_none()
                if build:
                    result.append('[%s] %s' % (build.get_status(), job_name))
                else:
                    result.append('[NOT BUILT] %s' % (job_name))

        if result:
            result_as_str = 'Current job status:\n'
            for i in result:
                result_as_str += ' - %s\n' % i

            msg.reply(result_as_str)

        else:
            msg.reply('Well, if you\'ve been there once, not anymore... loser!')


    @respond('.*show.*jobs.*')
    def show_jobs(self, brain, msg, match):
        username = self._username(brain, msg)
        if not username:
            return

        result = []
        job_patterns = brain.setdefault('jenkins_job_patterns', {})
        for job_pattern, usernames in job_patterns.iteritems():
            if username in usernames:
                result.append(job_pattern)

        if not result:
            msg.reply('I found no jobs for you :(')

        else:
            result_as_str = 'You are watching the following jobs:\n'
            for i in result:
                result_as_str += ' - %s\n' % i
            msg.reply(result_as_str)


    @respond('.*add me.* (.*)')
    @respond('.*add me.* (.*)[\.!?]^\*')
    @respond('.*add me.* (.*),')
    def add_me(self, brain, msg, match):
        username = self._username(brain, msg)
        if not username:
            return

        job_pattern = match.group(1)
        job_patterns = brain.setdefault('jenkins_job_patterns', {})
        usernames = job_patterns.setdefault(job_pattern, [])
        if username not in usernames:
            usernames.append(username)
            msg.reply('You are added to %s' % job_pattern)
        else:
            msg.reply('Again? You are already there!')


    @respond('.*remove me.* (.*)')
    @respond('.*remove me.* (.*)[\.!?]^\*')
    @respond('.*remove me.* (.*),')
    def remove_me(self, brain, msg, match):
        username = self._username(brain, msg)
        if not username:
            return

        job_pattern = match.group(1)
        job_patterns = brain.setdefault('jenkins_job_patterns', {})
        usernames = job_patterns.setdefault(job_pattern, [])
        if username in usernames:
            usernames.remove(username)
            msg.reply('You\'ve been removed from %s.' % job_pattern)
        else:
            msg.reply('Well, if you\'ve been there once, not anymore... loser!')

        if not usernames:
            del job_patterns[job_pattern]
