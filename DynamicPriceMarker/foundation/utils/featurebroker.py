""" Created a Feature broker which supports dependency injection

You can register a value, a function, an instance and a class
This value can then be retrieved later. The feature broker is based
on a singleton pattern, so you can use the class or the instance.

See file test_featurebroker.py for some examples on how to use it.

TO register a function, you can use the decorator defined like this:
@register_feature("test7")
def update_function():
    pass

Then the function can be called as FeatureBroker.test7(). Just including
the file with the decorator is sufficient to register the function

If you register a class like this:
    FeatureBroker.register('test4', MyTestItem)
with MyTestItem being a class with a default constructor, then upon each
retrieval, a new instance is created of that class.

If you register an instance:
    FeatureBroker.register('test4', MyTestItem())
Then the state is stored among different calls. Note that the instance should
not implement the __call__ method in this case, else that function will be
called upon retrieval

If you register a function and you use the
    FeatureBroker.register('test4', my_function)
then the function will be called without any arguments direct at the time
you are requesting teh resource. If that is not what you want, use the
following function:
    FeatureBroker.register_function('test4', my_function)
or use the above mentioned decorator

to give an example
def my_function():
    return 'edwin'

FeatureBroker.register('test4', my_function)
FeatureBroker.register_function('test5', my_function)

user1 = FeatureBroker.test4 # user1 = 'edwin'
user2 = FeatureBroker.test5() # user2 = 'edwin'

In the second way, you might provide extra arguments

"""
import re
from foundation.utils.customexceptions import ConfigurationError
import logging


# pylint: disable=protected-access

class Singleton(type):
    """ Singleton meta type. To make a class singleton declare class like this:
    class FeatureBroker(metaclass=Singleton):
    """
    _instance = None

    def __call__(cls, *args, **kwargs):
        """ Singleton realization """
        if not cls._instance:
            cls._instance = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instance

    def __getattr__(cls, item):
        """ Forward call to class (not instance) """
        raise AttributeError(f"'{cls.__name__}' object has no attribute '{item}'")

class FeatureIndexing(Singleton):
    """ Meta class to add direct access by name to the class as static method

     Needs to be derived from Singleton because we can only have one
     meta type as origin
     """

    def __getattr__(cls, item):
        """ Forward call to class (not instance) """
        if cls._instance:
            try:
                return cls._instance.get_item(item, True)
            except ConfigurationError:
                return super().__getattr__(item)
    
        return super().__getattr__(item)


class FeatureBroker(metaclass=FeatureIndexing):
    """ Register all resources here as callable functions, classes, instances or values """

    def __init__(self, allow_replace=True):
        """ Constructor - Singleton

        Args:
            allow_replace: boolean telling that overwrite is OK or not
        """
        ## The list of available features
        self.providers = {}
        self.features = {}
        ## whether or not featres are to be replaced once set
        self.allow_replace = allow_replace

    def provide(self, feature, provider):
        """ Register a provider as a feature

        Args:
            feature: String - name of feature to store
            provider: class, function or value to store
        """
        if not self.allow_replace and feature in self.providers:
            raise ConfigurationError(feature, "Feature already exists")
        self.providers[feature] = provider

    def get_item(self, item, raise_error=False):
        """ Get the resource by using []
        Args:
            item: string with name of a stored feature
        Return:
            the stored item (value, function or class or instance)
        """
        if item not in self.providers:
            if raise_error:
                raise ConfigurationError(item, "Feature does not exists")
            return None
        provider = self.providers.get(item)

        if callable(provider):
            return provider()
        return provider
    
    def remove_item(self, item):
        """ Remove a feature """
        if item in self.providers:
            del self.providers[item]
        else:
            logging.warning("Feature %s does not exist", item)

    def __getitem__(self, item):
        """ Get the resource by using []
        Args:
            item: string with name of a stored feature
        Return:
            the stored item (value, function or class or instance)
        """
        error = None
        try:
            provider = self.providers[item]
        except KeyError:
            error = ConfigurationError(item, "Feature does not exists")
        if error:
            raise error
        if callable(provider):
            return provider()
        return provider

    def __getattr__(self, item):
        """ Pretend that the item is a member of the instance """
        return self[item]

    @staticmethod
    def register(feature, provider):
        """ Register the provider as a provider for the feature

        Args:
            feature: String - name of feature to store
            provider: class, function or string to store
        """
        # This might happen with no instance present
        # Use constructor along with Singleton meta class to make this work
        FeatureBroker().provide(feature, provider)

    @staticmethod
    def remove(feature):
        """ Remove a feature """
        FeatureBroker._instance.remove_item(feature)


    @staticmethod
    def register_function(feature, provider):
        """ Register the provider as a provider for the feature

        Args:
            feature: String - name of feature to store
            provider: class, function or string to store
        """

        class Functor:
            """ Simple class to capture the execution of the function """

            def __init__(self, func):
                """ Constructor

                Args:
                    func: function to be captured
                """
                self.func = func

            def __call__(self):
                """ Callable return the func to neutralize the function call """
                return self.func

        FeatureBroker().provide(feature, Functor(provider))

    @staticmethod
    def get(feature):
        """
        Args:
            feature: Get a stored item
        Return:
            the stored item
        """
        # If there is no instance while getting, there is nothing to get
        # This is an error. Accessing private member because I know it's OK
        return FeatureBroker._instance[feature]

    @staticmethod
    def get_if_exists(feature, default):
        """
        Args:
            feature: Get a stored item
            default: Return default value if feature does not exist
        Return:
            the stored item or the default value
        """
        # If there is no instance while getting, there is nothing to get
        # This is an error. Accessing private member because I know its OK
        if not FeatureBroker._instance:
            return default
        return FeatureBroker._instance.providers.get(feature, default)

    @staticmethod
    def register_feature_flag(feature: str, enabled: bool):
        """Register a list of strings as supported features"""

        if not re.fullmatch("[a-zA-Z0-9_]+", feature):
            raise Exception(f"Feature {feature} contains non alphanumerical characters")

        FeatureBroker()._instance.features[feature] = enabled

    @staticmethod
    def unregister_feature_flag(feature: str):
        """Register a list of strings as supported features"""

        if feature in FeatureBroker()._instance.features:
            del FeatureBroker()._instance.features[feature]

    @staticmethod
    def has_feature_flag(feature: str):
        """Check if a feature is present in the list of features"""
        return feature in FeatureBroker()._instance.features

    @staticmethod
    def is_active_feature_flag(feature: str):
        """Check if a feature is active and in the list of features. If feature does not exist, it returns False"""
        return FeatureBroker()._instance.features.get(feature, False)

    @staticmethod
    def is_inactive_feature_flag(feature: str):
        """Check if a feature is existing and deactivated. If feature does not exist, it returns False"""
        return not FeatureBroker()._instance.features.get(feature, True)

    @staticmethod
    def get_feature_flags() -> list:
        """Register a list of strings as supported features"""
        return [item for item in FeatureBroker()._instance.features.keys()]

    @staticmethod
    def get_active_feature_flags() -> list:
        """Register a list of strings as supported features"""
        return [item for item, value in FeatureBroker()._instance.features.items() if value]


def register_function(name):
    """ Decorator to register a function

    Args:
        name: name to be used for registration
    """

    def register(func):
        """ Register function

        Args:
            Function to be used in the Registration
        returns the function itself
        """
        FeatureBroker.register_function(name, func)
        return func

    return register


def register_class(name):
    """ Decorator to register a class

    Args:
        name: name to be used for registration
    """

    def register(func):
        """ Register function

        Args:
            Function to be used in the Registration
        returns the function itself
        """
        FeatureBroker.register(name, func)
        return func

    return register
