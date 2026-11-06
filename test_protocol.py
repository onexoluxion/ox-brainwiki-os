import asyncio
import sys
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from ox_retrieval import BASE
async def main():
    async with Client(StdioTransport(command=sys.executable,args=[str(BASE/'ox_retrieval.py'),'serve'])) as c:
        names={t.name for t in await c.list_tools()}
        assert names=={'search','read','list','status'},names
        result=await c.call_tool('search',{'query':'WO-2048','mode':'exact'})
        assert 'shipment.md' in str(result)
        print('stdio discovery and exact search PASS')
asyncio.run(main())
