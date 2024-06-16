import asyncio
import datetime
import logging
import os

import croniter

from misc.config import Config
from misc.vk_client import VkClient
from models.vk import Message

logger = logging.getLogger(__name__)

PG_DUMP_COMMAND_TEMPLATE = "pg_dump -U {user} -d {database} -h {host} > {filepath}"


class DumperService:
    def __init__(
            self,
            loop: asyncio.AbstractEventLoop,
            config: Config,
    ):
        self.loop = loop
        self.config = config
        self.tries = 3
        self.task: asyncio.Task | None = loop.create_task(self.dump_task())

    async def dump_task(self):
        while True:
            try:
                sleep = self.get_seconds_to_next_event_by_cron(self.config.dumper.cron)
                logger.info(f"Schedule {sleep=}")
                await asyncio.sleep(sleep)

                filepath = f"dump_{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}.sql"
                for _ in range(self.tries):
                    success = await self.dump_db(
                        filepath=filepath
                    )
                    logger.info(f"Dumped {success=}")
                    if success:
                        break
                else:
                    continue

                for _ in range(self.tries):
                    send_success = await self.send_dump_file(filepath)
                    logger.info(f"Sent {send_success=}")
                    if send_success:
                        break

                os.remove(filepath)
            except (StopIteration, GeneratorExit, asyncio.CancelledError):
                break
            except Exception as e:
                logger.error(e)

    async def dump_db(
            self,
            filepath: str
    ) -> bool:
        command = PG_DUMP_COMMAND_TEMPLATE.format(
            user=self.config.dumper.user,
            database=self.config.dumper.db,
            host='db',
            filepath=filepath,
        )
        result = os.system(command)
        if result != 0:
            success = False
            logger.error(f"pg_dump failed with code {result}, command = {command}")
        else:
            success = True
        return success

    async def send_dump_file(self, filepath: str) -> bool:
        success = True
        client = VkClient(self.config.vk)
        try:
            peer_id = self.config.dumper.vk_peer_id or self.config.vk.main_user_id
            attachment = await client.upload.doc_message(
                peer_id=peer_id,
                doc_path=filepath,
                title=os.path.basename(filepath)
            )
            if attachment:
                result = await client.messages.send(
                    peer_id=peer_id,
                    message=Message(text='', attachment=attachment)
                )
                logger.info(result)
        except Exception as e:
            logger.error(e)
            success = False
        finally:
            await client.close()
        return success

    @staticmethod
    def get_seconds_to_next_event_by_cron(cron: str) -> float:
        now = datetime.datetime.utcnow()
        nxt: datetime.datetime = croniter.croniter(cron, now).get_next(datetime.datetime)
        return (nxt - now).total_seconds()

    def close(self):
        if self.task:
            self.task.cancel()
            self.task = None
