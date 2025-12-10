from locust import HttpUser, TaskSet, task

from core.environment.host import get_host_for_locust_testing


class CsvvalidationBehavior(TaskSet):
    def on_start(self):
        self.index()

    @task
    def index(self):
        response = self.client.get("/csvvalidation")

        if response.status_code != 200:
            print(f"Csvvalidation index failed: {response.status_code}")


class CsvvalidationUser(HttpUser):
    tasks = [CsvvalidationBehavior]
    min_wait = 5000
    max_wait = 9000
    host = get_host_for_locust_testing()
