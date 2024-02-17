run:
	docker compose down -v && \
	docker compose up --build --force-recreate

clean:
	docker compose down -v

stop:
	docker compose down

test:
	./executar-teste-local.sh
