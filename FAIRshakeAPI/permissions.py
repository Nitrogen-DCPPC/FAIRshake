from rest_framework import permissions
from . import models

class IdentifiablePermissions(permissions.BasePermission):
  def has_permission(self, request, view):
    if view.action == 'add':
      return request.user.is_authenticated
    else:
      return request.method in permissions.SAFE_METHODS

  def has_object_permission(self, request, view, obj):
    if request.method in permissions.SAFE_METHODS and view.action not in ['modify', 'delete']:
      return True
    else:
      return obj.authors and obj.authors.filter(id=request.user.id).exists()

class AssessmentPermissions(IdentifiablePermissions):
  def has_object_permission(self, request, view, obj):
    if request.method in permissions.SAFE_METHODS or view.action in ['modify', 'delete']:
      return True
    else:
      return obj.assessor == request.user

class AssessmentRequestPermissions(IdentifiablePermissions):
  def has_object_permission(self, request, view, obj):
    if request.method in permissions.SAFE_METHODS or view.action not in ['modify', 'delete']:
      return True
    else:
      return obj.requestor == request.user
