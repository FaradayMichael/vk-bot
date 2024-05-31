import asyncio
import datetime
import logging
import os

import croniter
import yadisk

from misc.config import Config

logger = logging.getLogger(__name__)

PG_DUMP_COMMAND_TEMPLATE = "pg_dump -U {user} -d {database} -h {host} > {filename}"


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

                filename = f"dump_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.sql"
                for _ in range(self.tries):
                    success = await self.dump_db(
                        filename=filename
                    )
                    logger.info(f"Dumped {success=}")
                    if success:
                        break
                else:
                    continue

                for _ in range(self.tries):
                    send_success = await self.send_yandex_disk(filename)
                    logger.info(f"Sent {send_success=}")
                    if send_success:
                        break
                else:
                    continue
            except (StopIteration, GeneratorExit, asyncio.CancelledError):
                break
            except Exception as e:
                logger.error(e)

    async def dump_db(
            self,
            filename: str
    ) -> bool:
        command = PG_DUMP_COMMAND_TEMPLATE.format(
            user=self.config.dumper.user,
            database=self.config.dumper.db,
            host='db',
            filename=filename,
        )
        result = os.system(command)
        if result != 0:
            success = False
            logger.error(f"pg_dump failed with code {result}, command = {command}")
        else:
            success = True
        return success

    async def send_yandex_disk(self, filename: str) -> bool:
        success = True
        client = yadisk.AsyncClient(token=self.config.dumper.yd_token)
        try:
            with open(filename, "rb") as f:
                result = await client.upload(
                    f,
                    os.path.join(self.config.dumper.base_folder, filename)
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
        now = datetime.datetime.now()
        nxt: datetime.datetime = croniter.croniter(cron, now).get_next(datetime.datetime)
        return (nxt - now).total_seconds()

    def close(self):
        if self.task:
            self.task.cancel()
            self.task = None
