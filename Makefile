IMAGE?=${DOCKERHUB_USERNAME}/telemetry-api
TAG?=dev

build:
	docker build -t $(IMAGE):$(TAG) .

push:
	docker push $(IMAGE):$(TAG)

tag:
	git tag v$(TAG)
	git push origin v$(TAG)

up:
	docker compose --env-file .env up -d

down:
	docker compose down

logs:
	docker compose logs -f

test:
	./verify.sh || true
