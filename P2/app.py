import pypeln as pl, json, asyncio, aiomysql
from quart import Quart, request, render_template

app = Quart(__name__)

# Create and Connect to a pool of connections to MySQL database
async def get_db_session():
    return await aiomysql.create_pool(
        host='127.0.0.1', port=3306, maxsize=100,
        user='root', password='mysql123', db='mysql',
        loop=None, autocommit=True, local_infile=True
    )

# This function will be called when a worker is instantiated
async def on_start():
    return dict(
        pool = await get_db_session()
    )

# This function will be called when a worker is finished its works
async def on_done(pool):
    pool.close()
    await pool.wait_closed()

# Create procedure for retrieving statistics regarding securities and RIAs
async def create_proc():
    pool = await get_db_session()

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('drop procedure if exists `get_sec`;')
            await cur.execute('drop procedure if exists `get_ria`;')
            await cur.execute(
                """
                create procedure `get_sec`(IN in_cik varchar(20), IN in_quarter varchar(10))
                BEGIN
                    select * from sec_stats where cik = in_cik and quarter = in_quarter;
                END
                """
            )
            await cur.execute(
                """
                create procedure `get_ria`(IN in_cik varchar(20), IN in_quarter varchar(10))
                BEGIN
                    select * from ria_stats where cik = in_cik and quarter = in_quarter;
                END
                """
            )
    pool.close()
    await pool.wait_closed()

# Retrieving statistics regarding securities
async def get_sec(data, pool):
    sec_rows = []
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.callproc('get_sec', data)
            sec_rows = await cur.fetchall()

    return sec_rows

# Retrieving statistics regarding RIAs
async def get_ria(data, pool):
    ria_wows = []
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.callproc('get_ria', data)
            ria_rows = await cur.fetchall()

    return ria_rows

async def pipe(cik, qtrs):
    data = [(cik, qtr) for qtr in qtrs]
    num_qrts = len(qtrs)

    # Create the procedure to retrieve statistics regarding securities and RIAs from 13F documents
    await create_proc()

    # Stage of the pipeline to retrieve statistics regarding securities from 13F documents
    sec_rows = await pl.task.map(
        get_sec, data, workers=5, maxsize=5,
        on_start=on_start, on_done=on_done
    )

    # Flatten the list of the lists of data into a list of data
    sec_rows = [item for sublist in sec_rows for item in sublist]

    sec_dicts = []
    for sec in sec_rows:
        sec_dicts.append({
            'cik': sec[1], 'quarter': sec[2], 'security': sec[3],
            'value': sec[4], 'shares': sec[5], 'weighting': sec[6]
        })

    # Stage of the pipeline to retrieve statistics regarding RIAs from 13F documents
    ria_rows = await pl.task.map(
        get_ria, data, workers=5, maxsize=5,
        on_start=on_start, on_done=on_done
    )

    # Flatten the list of the lists of data into a list of data
    ria_rows = [item for sublist in ria_rows for item in sublist]

    ria_dicts = []
    for ria in ria_rows:
        ria_dicts.append({
            'cik': ria[1], 'quarter': ria[2], 'num_sec': ria[3],
            'value': ria[4], 'shares': ria[5],
            'change_value': ria[6], 'change_shares': ria[7]
        })

    return sec_dicts, ria_dicts

# Routing to the website
@app.route('/', methods=['GET'])
async def index():
    cik = request.args.get('cik')
    start = request.args.get('start')
    end = request.args.get('end')

    pool = await get_db_session()

    sec_dicts = []
    ria_dicts = []
    qtrs = []

    qtr_rows = []
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                select distinct quarter from ria_stats 
                where cik = {cik} and quarter between "{start}" and "{end}"
                """
            )
            qtr_rows = await cur.fetchall()
    
    for qtr in qtr_rows:
        qtrs.append(qtr[0])

    sec_dicts, ria_dicts = await pipe(cik, qtrs)

    end = json.dumps(end, indent=2)
    sec_data = json.dumps(sec_dicts, indent=2)
    ria_data = json.dumps(ria_dicts, indent=2)
    data = {'end': end, 'sec_data': sec_data, 'ria_data': ria_data}

    pool.close()
    await pool.wait_closed()
    return await render_template('index.html', data=data)

if __name__ == '__main__':
    app.run(debug=True)