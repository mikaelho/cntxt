from cntxt import context

from samples.plugins.my_package import core_function
from samples.plugins.plugin import plugin


core_function = context.wrap(core_function, plugins=[plugin])
