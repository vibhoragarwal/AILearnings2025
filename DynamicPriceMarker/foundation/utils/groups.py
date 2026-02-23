"""Support for groups. Groups are considered case insentive

There is a special rule build in. If a group starts with skf_, it will automatically 
be applied to all internal users whether or nbot the group ios configured. For non-internal
ussers, the group must be explicitly configured

"""


# Special groups
# registered
# internal


class Groups:
    """Special class to support groups"""

    INTERNAL = "internal"
    REGISTERED = "registered"

    def __init__(self, groups: list, is_internal: bool = False, is_registered: bool = False):
        self.groups = {group.lower() for group in groups} if groups else set()
        if is_internal:
            self.groups.add(Groups.INTERNAL)
        if is_registered or is_internal:
            self.groups.add(Groups.REGISTERED)

    def __contains__(self, key):
        """Suport in"""
        # Allow for more intelligent checks
        group = key.lower()
        if group in self.groups:
            return True
        if group.startswith("skf_") and Groups.INTERNAL in self.groups:
            return True
        return False

    def append(self, group: str):
        """append a group and convert it to lower case"""
        self.groups.add(group.lower())

    def extend(self, new_groups: list):
        """append groups and convert to lower case"""
        # Allow for more intelligent checks
        self.groups.update([group.lower() for group in new_groups])

    def __iadd__(self, other):
        """Support += operatior"""
        if not other:
            return self.groups
        if isinstance(other, str):
            self.append(other)
        elif isinstance(other, list):
            self.extend(other)
        else:
            raise TypeError("Adding other types then string or list of string not supported")
        return self
