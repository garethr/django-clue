from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings

class Command(BaseCommand):
    help = "Run a development server with additional middleware"
        
    def handle(self, *args, **options):
      
        settings.MIDDLEWARE_CLASSES += (
          'clue.middleware.query.QueryMiddleware',
          'clue.middleware.profiler.ProfileMiddleware',
          'clue.middleware.template.TemplateMiddleware',
        )
      
        call_command('runserver')