from config.choices import EstadoEnvio


def estado_envio_choices(request):
    return {"estado_envio_choices": EstadoEnvio.choices}
