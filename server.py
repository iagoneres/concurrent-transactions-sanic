import asyncpg
import orjson
from sanic import Sanic, response

app = Sanic(__name__)

DB_NAME = "rinha_2024"
DB_USER = "postgres"
DB_PASSWORD = "postgres"
DB_HOST = "localhost"
DB_PORT = "5432"


async def create_pool():
    return await asyncpg.create_pool(
        database=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
    )


@app.listener("before_server_start")
async def setup_db(app, loop):
    app.ctx.db_pool = await create_pool()


@app.route("/clients", methods=["GET"])
async def get_clients(request):
    async with app.ctx.db_pool.acquire() as connection:
        query = "SELECT * FROM clients ORDER BY id"
        records = await connection.fetch(query)
        clients = [dict(record) for record in records]

        return response.raw(orjson.dumps({"results": clients}), content_type="application/json")


@app.route("/clients/<id:int>/transacoes", methods=["POST"])
async def create_transaction(request, id):
    data = request.json
    if data["tipo"] in ("c", "d"):
        async with app.ctx.db_pool.acquire() as connection:
            async with connection.transaction():
                query = 'SELECT balance, "limit" FROM clients WHERE id = $1 FOR UPDATE'
                client = await connection.fetchrow(query, id)

                if not client:
                    body = {"error": "Client not found"}
                    return response.raw(
                        orjson.dumps(body), status=404, content_type="application/json"
                    )
                balance, limit = client["balance"], client["limit"]

                if data["tipo"] == "c":
                    new_balance = balance + data["valor"]

                if data["tipo"] == "d":
                    if balance - data["valor"] < -limit:
                        body = {"error": "Insufficient funds"}
                        return response.raw(
                            orjson.dumps(body),
                            status=422,
                            content_type="application/json",
                        )
                    else:
                        new_balance = balance - data["valor"]

                query = 'INSERT INTO transactions (client_id, "value", "type", description) VALUES ($1, $2, $3, $4)'
                await connection.execute(query, id, data["valor"], data["tipo"], data["descricao"])

                query = "UPDATE clients SET balance = $1 WHERE id = $2"
                await connection.execute(query, new_balance, id)

                body = {"limite": limit, "saldo": new_balance}
                return response.raw(orjson.dumps(body), content_type="application/json")

    else:
        body = orjson.dumps({"error": "Invalid transaction type"})
        return response.raw(body, status=422, content_type="application/json")


@app.route("/clients/<id:int>/extrato", methods=["GET"])
async def get_statement(request, id):
    async with app.ctx.db_pool.acquire() as connection:
        query = 'SELECT balance, "limit" FROM clients WHERE id = $1'
        client = await connection.fetchrow(query, id)
        if not client:
            body = {"error": "Client not found"}
            return response.raw(orjson.dumps(body), status=404, content_type="application/json")

        query = 'SELECT "value", "type", description, performed_at FROM transactions WHERE client_id = $1 ORDER BY performed_at DESC LIMIT 5'
        transactions = await connection.fetch(query, id)

        # serializer transactions from valuem, type, description, performed_at to a list of dict of valor, tipo, descricao, realizada_em
        transactions = [
            {
                "valor": record["value"],
                "tipo": record["type"],
                "descricao": record["description"],
                "realizada_em": record["performed_at"],
            }
            for record in transactions
        ]

        body = {
            "saldo": client["balance"],
            "limite": client["limit"],
            "ultimas_transacoes": transactions,
        }
        return response.raw(orjson.dumps(body), content_type="application/json")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
