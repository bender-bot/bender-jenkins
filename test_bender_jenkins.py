def test_url(bender_tester, *args):
    m = bender_tester.user_send('jenkins get url')
    assert m.replies[0] == 'There is no such information available.'

    m = bender_tester.user_send('jenkins set url http://localhost:9090/')
    assert m.replies[0] == 'http://localhost:9090/ was added as Jenkins URL.'

    m = bender_tester.user_send('jenkins get url')
    assert m.replies[0] == 'URL: http://localhost:9090/'


def test_update_interval(bender_tester, *args):
    m = bender_tester.user_send('jenkins get update interval')
    assert m.replies[0] == 'There is no such information available.'

    m = bender_tester.user_send('jenkins set update interval 30')
    assert m.replies[0] == 'Jenkins update interval set to 30 seconds.'

    m = bender_tester.user_send('jenkins get update interval')
    assert m.replies[0] == 'Update interval: 30 seconds'


def test_job_status(bender_tester):
    m = bender_tester.user_send('jenkins job status app-.+')
    assert m.replies[0] == 'There is no Jenkins server set.'

    bender_tester.user_send('jenkins set url http://localhost:9090/')
    m = bender_tester.user_send('jenkins job status app-.+')
    assert m.replies[0] == 'This might take a while. Please wait...'
    assert 'Connection aborted' in m.replies[1]  # As no real connection exists


def test_notifications(bender_tester, *args):
    m = bender_tester.user_send('jenkins notify me app-.+')
    print m.replies

    # Show notifications ---------------------------------------------------------------------------
    m = bender_tester.user_send('jenkins show notifications')
    print m.replies

    # Remove notification --------------------------------------------------------------------------
    m = bender_tester.user_send('jenkins remove me app-.+')
    print m.replies
