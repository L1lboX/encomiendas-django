from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    scope = "login_attempt"


class EmpleadoRateThrottle(UserRateThrottle):
    scope = "empleado"


class CambioEstadoThrottle(UserRateThrottle):
    scope = "cambio_estado"


class BurstRateThrottle(AnonRateThrottle):
    scope = "burst"


class SustainedRateThrottle(UserRateThrottle):
    scope = "sustained"
