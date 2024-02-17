from datetime import datetime

import asyncpg
import orjson
from sanic import Sanic, response

from views.statements import StatementView
from views.transactions import TransactionView

app = Sanic("concurent_transactions")

DB_NAME = "rinha_2024"
DB_USER = "postgres"
DB_PASSWORD = "postgres"
DB_HOST = "db"
DB_PORT = "5432"


async def create_pool():
    return await asyncpg.create_pool(
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        max_inactive_connection_lifetime=30,
    )


@app.listener("before_server_start")
async def setup_db(app, loop):
    app.ctx.db_pool = await create_pool()


@app.listener("after_server_start")
async def load_clients(app, loop):
    async with app.ctx.db_pool.acquire() as connection:
        query = 'SELECT id, "limit" FROM clients'
        clients = await connection.fetch(query)
        app.ctx.clients = {client["id"]: client["limit"] for client in clients}


@app.listener("after_server_stop")
async def close_db(app, loop):
    await app.ctx.db_pool.close()


app.add_route(StatementView.as_view(), "/clientes/<id:int>/extrato")
app.add_route(TransactionView.as_view(), "/clientes/<id:int>/transacoes")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
