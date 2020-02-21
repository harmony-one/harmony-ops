const polka = require('polka');
const bodyParser = require('body-parser');
const { PORT } = require('./config');
const { hmy_latestHeader } = require('./RPC-calls/hmy_latestHeader')
const { hmy_getNodeMetadata } = require('./RPC-calls/hmy_getNodeMetadata')
const { hmy_getPendingCxReceipts } = require('./RPC-calls/hmy_getPendingCxReceipts')

//initialize polka
const app = polka();

//set headers for response
app.use((req, res, next) => {
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('Vary', 'Origin');
    next();
});

//use bodyParser to get JSON from request body
app.use(bodyParser.json());

//main mock logic on base path
app.post('/', (req, res) => {
    const json = req.body;

    //each RPC call is a different switch case
    switch (json.method) {
        case 'hmy_latestHeader':
            res.end(hmy_latestHeader(json.id));
            break;
        case 'hmy_getNodeMetadata':
            res.end(hmy_getNodeMetadata(json.id));
            break;
        case 'hmy_getPendingCxReceipts':
            res.end(hmy_getPendingCxReceipts(json.id));
            break;
        default:
            res.end(JSON.stringify({
                "jsonrpc": "2.0",
                "id": 1,
                "error": {
                    "code": -32601,
                    "message": `The method ${json.method} does not exist/is not available`
                }
            }));
            break;
    }
})

//start the server
app.listen(PORT, err => {
        if (err) throw err;
        console.log(`Server started on http://localhost:${PORT}/`);
})