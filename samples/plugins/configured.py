from cntxt import cntxt

from samples.plugins.my_package import core_function
from samples.plugins.plugin import plugin


core_function = cntxt.wrap(core_function, plugins=[plugin])
