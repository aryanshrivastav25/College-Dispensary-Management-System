# campuscare/core/templatetags/role_tags.py — Step 3
from django import template
from django.template import Node, NodeList, TemplateSyntaxError

from core.decorators import user_has_any_role

register = template.Library()


class IfRoleNode(Node):
    """Render the appropriate branch when the current user has a matching role."""

    def __init__(self, allowed_roles: tuple[str, ...], true_branch: NodeList, false_branch: NodeList):
        self.allowed_roles = allowed_roles
        self.true_branch = true_branch
        self.false_branch = false_branch

    def render(self, context) -> str:
        request = context.get('request')
        user = getattr(request, 'user', None)

        if user and user_has_any_role(user, self.allowed_roles):
            return self.true_branch.render(context)

        return self.false_branch.render(context)


@register.tag(name='if_role')
def if_role(parser, token):
    """Render a block only when the authenticated user has one of the listed roles."""
    bits = token.split_contents()
    if len(bits) < 2:
        raise TemplateSyntaxError("if_role requires at least one role, for example {% if_role 'doctor' %}.")

    allowed_roles = tuple(bit.strip("'\"") for bit in bits[1:])
    true_branch = parser.parse(('else', 'endif_role'))
    next_token = parser.next_token()

    if next_token.contents == 'else':
        false_branch = parser.parse(('endif_role',))
        parser.delete_first_token()
    else:
        false_branch = NodeList()

    return IfRoleNode(allowed_roles, true_branch, false_branch)
