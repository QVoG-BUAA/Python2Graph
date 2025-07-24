def barrier(x):
    return escape(x)

source = request.get("password")
pw = barrier(source)
sink(pw)
