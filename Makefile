db-init:
	alembic upgrade head

db-rev:
	alembic revision --autogenerate -m "$(m)"

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

test-phase-b:
	API=http://localhost KEY=TEST_KEY ADMIN_KEY=ADMIN_SOURCES_TEST bash scripts/test_phase_b.sh

# Feature flag management
.PHONY: flags-show flags-http-on flags-http-off flags-logonly-on flags-logonly-off
API ?= http://localhost
ADMIN_KEY ?= ADMIN_SOURCES_TEST

flags-show:
	curl -s -H "Authorization: Bearer $(ADMIN_KEY)" $(API)/v1/admin/featureflags | jq

flags-http-on:
	curl -s -X PATCH -H "Authorization: Bearer $(ADMIN_KEY)" -H "Content-Type: application/json" \
	  -d '{"ADMISSION_HTTP_ENABLED":true}' $(API)/v1/admin/featureflags | jq

flags-http-off:
	curl -s -X PATCH -H "Authorization: Bearer $(ADMIN_KEY)" -H "Content-Type: application/json" \
	  -d '{"ADMISSION_HTTP_ENABLED":false}' $(API)/v1/admin/featureflags | jq

flags-logonly-on:
	curl -s -X PATCH -H "Authorization: Bearer $(ADMIN_KEY)" -H "Content-Type: application/json" \
	  -d '{"ADMISSION_LOG_ONLY":true}' $(API)/v1/admin/featureflags | jq

flags-logonly-off:
	curl -s -X PATCH -H "Authorization: Bearer $(ADMIN_KEY)" -H "Content-Type: application/json" \
	  -d '{"ADMISSION_LOG_ONLY":false}' $(API)/v1/admin/featureflags | jq

test-phase-b5:
	chmod +x scripts/test_phase_b5_flags.sh && API=$(API) ADMIN_KEY=$(ADMIN_KEY) KEY=$(KEY) bash scripts/test_phase_b5_flags.sh

test-phase-b5-simple:
	chmod +x scripts/test_phase_b5_simple.sh && API=$(API) ADMIN_KEY=$(ADMIN_KEY) KEY=$(KEY) bash scripts/test_phase_b5_simple.sh

test-phase-b2:
	chmod +x scripts/test_phase_b2.sh && API=$(API) ADMIN_KEY=$(ADMIN_KEY) KEY=$(KEY) bash scripts/test_phase_b2.sh

# Firewall management
.PHONY: firewall-sync firewall-show firewall-status firewall-setup
API ?= http://localhost
ADMIN_KEY ?= ADMIN_SOURCES_TEST

firewall-sync:
	curl -s -X POST -H "Authorization: Bearer $(ADMIN_KEY)" $(API)/v1/admin/security/sync-allowlist | jq

firewall-show:
	sudo nft list set inet telemetry exporters | sed -n '1,80p'

firewall-status:
	curl -s -H "Authorization: Bearer $(ADMIN_KEY)" $(API)/v1/admin/security/allowlist/status | jq

firewall-setup:
	sudo nft add table inet telemetry || true
	sudo nft add set inet telemetry exporters { type ipv4_addr; flags interval; } || true
	sudo nft add set inet telemetry exporters6 { type ipv6_addr; flags interval; } || true
	sudo nft add chain inet telemetry input { type filter hook input priority 0; policy accept; } || true
	sudo nft add rule inet telemetry input udp dport 2055 ip saddr @exporters accept || true
	sudo nft add rule inet telemetry input udp dport 2055 ip6 saddr @exporters6 accept || true
	sudo nft add rule inet telemetry input udp dport 2055 drop || true

test-phase-c1:
	chmod +x scripts/test_phase_c1.sh && API=$(API) ADMIN_KEY=$(ADMIN_KEY) KEY=$(KEY) bash scripts/test_phase_c1.sh

test-phase-c1-simple:
	chmod +x scripts/test_phase_c1_simple.sh && API=$(API) ADMIN_KEY=$(ADMIN_KEY) KEY=$(KEY) bash scripts/test_phase_c1_simple.sh

test-zero-to-hero:
	chmod +x scripts/test_zero_to_hero.sh && API=$(API) ADMIN_KEY=$(ADMIN_KEY) KEY=$(KEY) bash scripts/test_zero_to_hero.sh

# C1 Polish - Linux production runbook & robustness
firewall-dryrun:
	curl -s -X POST -H "Authorization: Bearer $(ADMIN_KEY)" "$(API)/v1/admin/security/sync-allowlist?dry_run=true" | jq

# B5 Polish - Feature flags UX
flags-toggle-log-only:
	curl -s -X PATCH -H "Authorization: Bearer $(ADMIN_KEY)" -H "Content-Type: application/json" -d '{"ADMISSION_LOG_ONLY":true}' "$(API)/v1/admin/featureflags" | jq
