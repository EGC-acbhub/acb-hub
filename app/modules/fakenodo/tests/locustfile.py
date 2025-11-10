from locust import HttpUser, TaskSet, task
from core.environment.host import get_host_for_locust_testing
from core.locust.common import get_csrf_token


class FakenodoBehavior(TaskSet):
    def on_start(self):
        self.login()

    def login(self):
        response = self.client.get("/login")
        csrf_token = get_csrf_token(response)

        self.client.post("/login", data={
            "email": "user1@example.com",
            "password": "1234",
            "csrf_token": csrf_token
        })

    @task(1)
    def index(self):
        self.client.get("/dataset/upload")

    @task(2)
    def view_datasets(self):
        self.client.get("/dataset/list")


class FakenodoUser(HttpUser):
    tasks = [FakenodoBehavior]
    min_wait = 5000
    max_wait = 9000
    host = get_host_for_locust_testing()
