from cntxt import context


def core_function() -> list[str]:
    result = ["main"]

    for plugin in context["plugins"]:
        result.append(plugin())

    return result
