from django.db import models
from django.conf import settings

'''
class Role(models.Model):
    """Role definition for RBAC."""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Permission(models.Model):
    """Permission definition for RBAC."""
    code = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.code


class RolePermission(models.Model):
    """Links roles to permissions."""
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("role", "permission")

    def __str__(self):
        return f"{self.role.name} -> {self.permission.code}"


class UserRole(models.Model):
    """Links users to roles."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "role")

    def __str__(self):
        return f"{self.user.email} -> {self.role.name}"


def user_has_permission(user, permission_code):
    # example code: can_delete_post
    """Check if a user has a specific permission."""
    if not user.is_authenticated:
        return False
    return RolePermission.objects.filter(
        role__userrole__user=user,
        permission__code=permission_code
    ).exists()


def assign_role(user, role_name):
    """Assign a role to a user."""
    role, created = Role.objects.get_or_create(name=role_name)
    UserRole.objects.get_or_create(user=user, role=role)
    return role


def remove_role(user, role_name):
    """Remove a role from a user."""
    UserRole.objects.filter(user=user, role__name=role_name).delete()
'''
