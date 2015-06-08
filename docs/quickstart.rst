.. This file is built from docs/quickstart.rst.j2; do not edit!

Quickstart
==========

Here's an example script.  The file is also viewable here_.

.. _here: https://github.com/scriptharness/python-scriptharness/blob/win_unicode/examples/quickstart.py

::

    #!/usr/bin/env python
    # -*- coding: utf-8 -*-
    # This file is formatted slightly differently for readability in ReadTheDocs.
    """python-scriptharness quickstart example.
    
    This file can be found in the examples/ directory of the source at
    https://github.com/scriptharness/python-scriptharness
    """
    from __future__ import absolute_import, division, print_function, \
                           unicode_literals
    import scriptharness
    import scriptharness.commands
    
    """First, define functions for all actions.  Each action MUST have a function
    defined.  The function should be named the same as the action.  (If the
    action has a `-` in it, replace it with an `_`; e.g. an action named
    `upload-to-s3` would call the `upload_to_s3()` function.  Each action function
    will take a single argument, `context`.
    
    Each action function should be idempotent, and able to run standalone.
    In this example, `package` may require that the steps in `build` ran at
    some point before `package` is run, but we can't assume that happened in
    the same script run.  It could have happened yesterday, or three weeks ago,
    and `package` should still be able to run.  If you need to save state
    between actions, consider saving state to disk.
    """
    def clobber(context):
        """Clobber the source"""
        context.logger.info("log message from clobber")
    
    def pull(context):
        """Pull source"""
        context.logger.info("log message from pull")
    
    def build(context):
        """Build source"""
        context.logger.info("log message from build")
        if context.config.get("new_argument"):
            context.logger.info("new_argument is set to %s",
                                context_config['new_argument'])
    
    def package(context):
        """Package source"""
        context.logger.info("log message from package")
        scriptharness.commands.run(
            ['python', '-c',
             "from __future__ import print_function; print('hello world!')"]
        )
    
    def upload(context):
        """Upload packages"""
        context.logger.info("log message from upload")
    
    def notify(context):
        """Notify watchers"""
        context.logger.info("log message from notify")
    
    
    if __name__ == '__main__':
        """Enable logging to screen + artifacts/log.txt.  Not required, but
        without it the script will run silently.
        """
        scriptharness.prepare_simple_logging("artifacts/log.txt")
    
        """Define actions.  All six actions are available to run, but if the
        script is run without any action commandline options, only the
        enabled actions will run.
    
        If default_actions is specified, it MUST be a subset of all_actions
        (the first list), and any actions in default_actions will be enabled
        by default (the others will be disabled).  If default_actions isn't
        specified, all the actions are enabled.
    
        Each action MUST have a function defined (see above).
        """
        actions = scriptharness.get_actions_from_list(
            ["clobber", "pull", "build", "package", "upload", "notify"],
            default_actions=["pull", "build", "package"]
        )
    
        """Create a commandline argument parser, with default scriptharness
        argument options pre-populated.
        """
        parser = scriptharness.get_parser(all_actions=actions)
    
        """Add new commandline argument(s)
        https://docs.python.org/dev/library/argparse.html#argparse.ArgumentParser.add_argument
        """
        parser.add_argument("--new-argument", action='store',
                            help="help message for --new-argument")
    
        """Create the Script object.  If ``get_script()`` is called a second time,
        it will return the same-named script object.  (`name` in get_script()
        defaults to "root".  We'll explore running multiple Script objects within
        the same script in the not-distant future.)
    
        When this Script object is created, it will parse all commandline
        arguments sent to the script.  So it doesn't matter that this script
        (quickstart.py) didn't have the --new-argument option until one line
        above; the Script object will parse it and store the new_argument
        value in its config.
        """
        script = scriptharness.get_script(actions=actions, parser=parser)
    
        """This will run the script.
        Essentially, it will go through the list of actions, and if the action
        is enabled, it will run the associated function.
        """
        script.run()


######
output
######

If you run this without any arguments, you might get output like this::

    $ ./quickstart.py
    00:00:00     INFO - Starting at 2015-05-25 00:00 PDT.
    00:00:00     INFO - Enabled actions:
    00:00:00     INFO -  pull, build, package
    00:00:00     INFO - {'new_argument': None,
    00:00:00     INFO -  'scriptharness_artifact_dir': '/src/python-scriptharness/docs/artifacts',
    00:00:00     INFO -  'scriptharness_base_dir': '/src/python-scriptharness/docs',
    00:00:00     INFO -  'scriptharness_work_dir': '/src/python-scriptharness/docs/build'}
    00:00:00     INFO - Creating directory /src/python-scriptharness/docs/artifacts
    00:00:00     INFO - Already exists.
    00:00:00     INFO - ### Skipping action clobber
    00:00:00     INFO - ### Running action pull
    00:00:00     INFO - log message from pull
    00:00:00     INFO - ### Action pull: finished successfully
    00:00:00     INFO - ### Running action build
    00:00:00     INFO - log message from build
    00:00:00     INFO - ### Action build: finished successfully
    00:00:00     INFO - ### Running action package
    00:00:00     INFO - log message from package
    00:00:00     INFO - Running command: ['python', '-c', "from __future__ import print_function; print('hello world!')"]
    00:00:00     INFO - Copy/paste: python -c "from __future__ import print_function; print('hello world!')"
    00:00:00     INFO -  hello world!
    00:00:00     INFO - ### Action package: finished successfully
    00:00:00     INFO - ### Skipping action upload
    00:00:00     INFO - ### Skipping action notify
    00:00:00     INFO - Done.


First, it announced it's starting the script.  Next, it outputs the running
config, also saving it to the file ``artifacts/localconfig.json``.  Then it
logs each action as it runs enabled actions and skips disabled actions.
Finally, it announces 'Done.'.

The same output is written to the file ``artifacts/log.txt``.

#########
--actions
#########

You can change which actions are run via the ``--actions`` option::

    $ ./quickstart.py --actions package upload notify
    00:00:05     INFO - Starting at 2015-05-25 00:00 PDT.
    00:00:05     INFO - Enabled actions:
    00:00:05     INFO -  package, upload, notify
    00:00:05     INFO - {'new_argument': None,
    00:00:05     INFO -  'scriptharness_artifact_dir': '/src/python-scriptharness/docs/artifacts',
    00:00:05     INFO -  'scriptharness_base_dir': '/src/python-scriptharness/docs',
    00:00:05     INFO -  'scriptharness_work_dir': '/src/python-scriptharness/docs/build'}
    00:00:05     INFO - Creating directory /src/python-scriptharness/docs/artifacts
    00:00:05     INFO - Already exists.
    00:00:05     INFO - ### Skipping action clobber
    00:00:05     INFO - ### Skipping action pull
    00:00:05     INFO - ### Skipping action build
    00:00:05     INFO - ### Running action package
    00:00:05     INFO - log message from package
    00:00:05     INFO - Running command: ['python', '-c', "from __future__ import print_function; print('hello world!')"]
    00:00:05     INFO - Copy/paste: python -c "from __future__ import print_function; print('hello world!')"
    00:00:05     INFO -  hello world!
    00:00:05     INFO - ### Action package: finished successfully
    00:00:05     INFO - ### Running action upload
    00:00:05     INFO - log message from upload
    00:00:05     INFO - ### Action upload: finished successfully
    00:00:05     INFO - ### Running action notify
    00:00:05     INFO - log message from notify
    00:00:05     INFO - ### Action notify: finished successfully
    00:00:05     INFO - Done.


##############
--list-actions
##############

If you want to list which actions are available, and which are enabled by
default, use the ``--list-actions`` option::

    $ ./quickstart.py --list-actions
      clobber ['all']
    * pull ['all']
    * build ['all']
    * package ['all']
      upload ['all']
      notify ['all']


#############
--dump-config
#############

You can change the ``new_argument`` value in the config via the
``--new-argument`` option that the script added.  Also, if you just want to
see what the config is without running anything, you can use the
``--dump-config`` option::

    $ ./quickstart.py --new-argument foo --dump-config
    00:00:14     INFO - Dumping config:
    00:00:14     INFO - {'new_argument': 'foo',
    00:00:14     INFO -  'scriptharness_artifact_dir': '/src/python-scriptharness/docs/artifacts',
    00:00:14     INFO -  'scriptharness_base_dir': '/src/python-scriptharness/docs',
    00:00:14     INFO -  'scriptharness_work_dir': '/src/python-scriptharness/docs/build'}
    00:00:14     INFO - Creating directory /src/python-scriptharness/docs/artifacts
    00:00:14     INFO - Already exists.


######
--help
######

You can always use the ``--help`` option::

    $ ./quickstart.py --help
    usage: quickstart.py [-h] [--list-actions] [--actions ACTION [ACTION ...]]
                         [--skip-actions ACTION [ACTION ...]]
                         [--add-actions ACTION [ACTION ...]]
                         [--action-group {all,none}] [--config-file CONFIG_FILE]
                         [--opt-config-file CONFIG_FILE] [--dump-config]
                         [--new-argument NEW_ARGUMENT]
    
    optional arguments:
      -h, --help            show this help message and exit
      --list-actions        List all actions (default prepended with '*') and
                            exit.
      --actions ACTION [ACTION ...]
                            Specify the actions to run.
      --skip-actions ACTION [ACTION ...]
                            Specify the actions to skip.
      --add-actions ACTION [ACTION ...]
                            Specify the actions to add to the default set.
      --action-group {all,none}
                            Specify the action group to use.
      --config-file CONFIG_FILE, --cfg CONFIG_FILE, -c CONFIG_FILE
                            Specify required config files/urls
      --opt-config-file CONFIG_FILE, --opt-cfg CONFIG_FILE
                            Specify optional config files/urls
      --dump-config         Log the built configuration and exit.
      --new-argument NEW_ARGUMENT
                            help message for --new-argument

