import docker

from .config import config


def get_docker_client():
    return docker.DockerClient(base_url=config.DOCKER_HOST)

