from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from payments.models import Profile, Vendor, Project

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

        vendors_data = [
            ('Metro Hardware Ltd.', 'Construction materials'),
            ('Prime Cement Supplies', 'Cement'),
            ('SwiftHaul Logistics', 'Transport'),
            ('PowerHire Kenya', 'Equipment rental'),
            ('Apex Electricals', 'Electrical materials'),
            ('BlueLine Plumbing', 'Plumbing services'),
        ]
        for name, service in vendors_data:
            vendor, created = Vendor.objects.get_or_create(name=name, defaults={'service': service})
            status = 'Created' if created else 'Already exists'
            self.stdout.write(f'{status}: vendor {name}')

        projects_data = ['Westlands Project', 'Mombasa Road Project', 'Kisumu Project']
        for name in projects_data:
            project, created = Project.objects.get_or_create(name=name)
            status = 'Created' if created else 'Already exists'
            self.stdout.write(f'{status}: project {name}')