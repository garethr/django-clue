from django.core.management.base import BaseCommand
from optparse import make_option
import sys

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--verbosity', action='store', dest='verbosity', default='1',
            type='choice', choices=['0', '1', '2'],
            help='Verbosity level; 0=minimal output, 1=normal output, 2=all output'),
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help='Tells Django to NOT prompt the user for input of any kind.'),
        make_option('--coverage', action='store_true', dest='coverage', default=False,
            help='Show coverage details'),
        make_option('--figleaf', action='store_true', dest='figleaf', default=False,
            help='Produce figleaf coverage report'),
        make_option('--xml', action='store_true', dest='xml', default=False,
            help='Produce xml output for cruise control'),
    )
    help = 'Custom test command which allows for specifying different test runners.'
    args = '[appname ...]'

    requires_model_validation = False

    def handle(self, *test_labels, **options):
        from django.conf import settings
        from django.db.models import get_app, get_apps

        verbosity = int(options.get('verbosity', 1))
        interactive = options.get('interactive', True)

        if options.get('coverage'):
            test_runner_name = 'clue.testrunners.codecoverage.run_tests'
        elif options.get('figleaf'):
            test_runner_name = 'clue.testrunners.figleafcoverage.run_tests'
        elif options.get('xml'):
            test_runner_name = 'clue.testrunners.xmloutput.run_tests'
        else:
            test_runner_name = settings.TEST_RUNNER
        
        test_path = test_runner_name.split('.')
        # Allow for Python 2.5 relative paths
        if len(test_path) > 1:
            test_module_name = '.'.join(test_path[:-1])
        else:
            test_module_name = '.'
        test_module = __import__(test_module_name, {}, {}, test_path[-1])
        test_runner = getattr(test_module, test_path[-1])

        failures = test_runner(test_labels, verbosity=verbosity, interactive=interactive)
        if failures:
            sys.exit(failures)