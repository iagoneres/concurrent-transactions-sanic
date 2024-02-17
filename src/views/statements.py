from datetime import datetime

import orjson
from sanic import HTTPResponse, Request, response
from sanic.views import HTTPMethodView


class StatementView(HTTPMethodView):
    async def get(self, request: Request, id: int) -> HTTPResponse:
        loaded_clients = request.app.ctx.clients
        if id not in loaded_clients:
            body = {"error": "Client not found"}
            return response.raw(orjson.dumps(body), status=404, content_type="application/json")

        async with request.app.ctx.db_pool.acquire() as connection:
            query = 'SELECT balance, "limit" FROM clients WHERE id = $1'
            client = await connection.fetchrow(query, id)

            query = 'SELECT "value", "type", description, performed_at FROM transactions WHERE client_id = $1 ORDER BY performed_at DESC LIMIT 5'
            transactions_response = await connection.fetch(query, id)

        transactions = [
            {
                "valor": record["value"],
                "tipo": record["type"],
                "descricao": record["description"],
                "realizada_em": record["performed_at"],
            }
            for record in transactions_response
        ]

        body = {
            "saldo": {
                "total": client["balance"],
                "data_extrato": datetime.utcnow(),
                "limite": client["limit"],
            },
            "ultimas_transacoes": transactions,
        }

        return response.raw(orjson.dumps(body), content_type="application/json")
