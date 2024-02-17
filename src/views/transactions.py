import re

import orjson
from sanic import HTTPResponse, Request, response
from sanic.views import HTTPMethodView


class Validator:
    def __init__(self):
        self.validations = []

    def add_validation(self, field, validation_func, error_message, status=422):
        self.validations.append(
            {
                "field": field,
                "func": validation_func,
                "error": error_message,
                "status": status,
            }
        )

    async def validate(self):
        for validation in self.validations:
            if not validation["func"](validation["field"]):
                body = orjson.dumps({"error": validation["error"]})
                return response.raw(
                    body, status=validation["status"], content_type="application/json"
                )


class TransactionView(HTTPMethodView):
    async def post(self, request: Request, id: int) -> HTTPResponse:
        loaded_clients = request.app.ctx.clients
        if id not in loaded_clients:
            body = {"error": "Client not found"}
            return response.raw(orjson.dumps(body), status=404, content_type="application/json")

        data = request.json
        transaction_type = data.get("tipo", "")
        transaction_value = data.get("valor", "")
        transaction_description = data.get("descricao", "")
        limit = loaded_clients[id]

        if transaction_type == "d" and transaction_value > limit:
            body = {"error": "Invalid value. Must be less than or equal to the client's limit."}
            return response.raw(orjson.dumps(body), status=422, content_type="application/json")

        transaction_type_regex = re.compile(r"^[cd]$")
        description_regex = re.compile(r"^\w{1,10}$")

        validator = Validator()
        validator.add_validation(
            transaction_type,
            lambda x: transaction_type_regex.match(x),
            "Invalid transaction type. Must be 'c' or 'd'.",
        )
        validator.add_validation(
            transaction_value, lambda x: isinstance(x, int), "Invalid value. Must be an integer."
        )
        validator.add_validation(
            transaction_description,
            lambda x: x is not None and description_regex.match(x),
            "Invalid description. Must be a string between 1 and 10 characters.",
        )

        error_response = await validator.validate()
        if error_response:
            return error_response

        async with request.app.ctx.db_pool.acquire() as connection:
            async with connection.transaction():
                query = "SELECT balance FROM clients WHERE id = $1 FOR UPDATE"
                client = await connection.fetchrow(query, id)
                balance = client["balance"]

                if transaction_type == "c":
                    new_balance = balance + transaction_value
                else:
                    if balance - transaction_value < -limit:
                        body = {"error": "Insufficient funds"}
                        return response.raw(
                            orjson.dumps(body),
                            status=422,
                            content_type="application/json",
                        )
                    new_balance = balance - transaction_value

                query = "UPDATE clients SET balance = $1 WHERE id = $2"
                await connection.execute(query, new_balance, id)

            query = 'INSERT INTO transactions (client_id, "value", "type", description) VALUES ($1, $2, $3, $4)'
            await connection.execute(
                query, id, transaction_value, transaction_type, transaction_description
            )

            body = {"limite": limit, "saldo": new_balance}
            return response.raw(orjson.dumps(body), content_type="application/json")
