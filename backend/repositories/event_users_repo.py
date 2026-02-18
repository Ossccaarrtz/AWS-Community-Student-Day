import os
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from db.dynamo import get_table

TICKET_GSI = os.getenv("TICKET_GSI_NAME", "TicketIdIndex")

class EventUsersRepo:
    @staticmethod
    def get_by_ticket_id(ticket_id: str) -> dict | None:
        table = get_table()

        resp = table.query(
            IndexName=TICKET_GSI,
            KeyConditionExpression=Key("ticketId").eq(ticket_id),
            ProjectionExpression="#uid, #tid, #name, #prof, checkedIn, checkedInAt",
            ExpressionAttributeNames={
                "#uid": "userId",
                "#tid": "ticketId",
                "#name": "name",
                "#prof": "profession",
            },
        )

        items = resp.get("Items", [])
        return items[0] if items else None

    @staticmethod
    def mark_checkin(user_id: str, now_iso: str) -> tuple[dict, bool]:
        """
        Regresa: (updated_item, already_checked_in)
        Requiere dynamodb:UpdateItem
        """
        table = get_table()
        try:
            upd = table.update_item(
                Key={"userId": user_id},
                UpdateExpression="SET checkedIn = :true, checkedInAt = :now",
                ConditionExpression="attribute_not_exists(checkedIn) OR checkedIn = :false",
                ExpressionAttributeValues={
                    ":true": True,
                    ":false": False,
                    ":now": now_iso
                },
                ReturnValues="ALL_NEW",
            )
            return upd.get("Attributes", {}), False
        except table.meta.client.exceptions.ConditionalCheckFailedException:
            # ya estaba marcado
            # NOTA: aquí no tenemos el item completo, el controller lo puede usar del query
            return {}, True
