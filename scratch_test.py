import asyncio
from temporalio.client import Client

async def test():
    c = await Client.connect('localhost:7233')
    w_iter = c.list_workflows("WorkflowType='ReminderWorkflow'")
    async for w in w_iter:
        if "demo" in w.id:
            print(w.id, w.status)

asyncio.run(test())
