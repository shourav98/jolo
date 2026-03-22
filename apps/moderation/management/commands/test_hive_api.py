import json
from django.core.management.base import BaseCommand
from apps.moderation.services import moderate_text, moderate_visual

class Command(BaseCommand):
    help = "Test Hive API connection for text and visual moderation"

    def handle(self, *args, **options):
        # 1. Test Text
        text_to_test = "I want to kill someone"
        self.stdout.write(self.style.WARNING(f"\n[TEXT] Testing: '{text_to_test}'"))
        res_text = moderate_text(text_to_test)
        self.stdout.write(self.style.SUCCESS(json.dumps(res_text, indent=2)))

        clean_text = "Have a great day!"
        self.stdout.write(self.style.WARNING(f"\n[TEXT] Testing: '{clean_text}'"))
        res_clean = moderate_text(clean_text)
        self.stdout.write(self.style.SUCCESS(json.dumps(res_clean, indent=2)))

        # 2. Test Visual
        nsfw_url = "https://d24edro6ichpbm.thehive.ai/demo_static_media/nsfw/nsfw_4.jpg"
        self.stdout.write(self.style.WARNING(f"\n[VISUAL] Testing NSFW url: {nsfw_url}"))
        res_vis = moderate_visual(nsfw_url)
        self.stdout.write(self.style.SUCCESS(json.dumps(res_vis, indent=2)))
