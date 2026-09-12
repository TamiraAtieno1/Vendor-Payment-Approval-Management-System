from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from payments.models import Profile

class Command(BaseCommand):
    help = 'Seeds the six sample users from the case study'

    def handle(self, *args, **kwargs):
        users_data = [
            ('alice', 'Alice Mwangi', Profile.EMPLOYEE),
            ('brian', 'Brian Otieno', Profile.EMPLOYEE),
            ('carol', 'Carol Wanjiku', Profile.MANAGER),
            ('david', 'David Mutua', Profile.MANAGER),
            ('faith', 'Faith Njeri', Profile.FINANCE),
            ('grace', 'Grace Kamau', Profile.ADMIN),
        ]

        for username, full_name, role in users_data:
            first_name, last_name = full_name.split(' ', 1)
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'first_name': first_name, 'last_name': last_name}
            )
            if created:
                user.set_password('password123')
                user.save()

            Profile.objects.get_or_create(user=user, defaults={'role': role})

            status = 'Created' if created else 'Already exists'
            self.stdout.write(f'{status}: {username} ({role})')