# toychain API

## Public API

### BALANCES

#### Get balances: `GET /balances/<address>`

example:
`GET /balances/b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d`

response:
- `200`:
```
{
    "balance": 50
}
```

### BLOCKS

#### Get block: `GET /blocks/<block-hash>`

example:
`GET /blocks/00000652676efb2ebcbde6aa2c1aa3212d4f06c3ee102638a5add0a64a5620a2`

response:
- `200`:
```
{
  "timestamp": 1652742613642125100,
  "prev": "00000ff249a92ae61550eb3086c59abf181aec8ef67c55cd30bbea74a3e51152",
  "nonce": 560239,
  "hash": "00000652676efb2ebcbde6aa2c1aa3212d4f06c3ee102638a5add0a64a5620a2",
  "transactions": [
    {
      "inputs": [
        {
          "transaction_id": "d0d9da8e1c009d6c19854d7bc0bce911c4e94afb86b9cfbcf0ce7e8004bf19b8",
          "vout": 0
        }
      ],
      "outputs": [
        {
          "address": "b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225",
          "amount": 10
        },
        {
          "address": "b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d",
          "amount": 35
        }
      ],
      "timestamp": 1652550310128397000,
      "signature": "cDf/+00aNMis90SJGYEDzAYbirT51ZXslGpUnd+jmCU/jGiBHRW+9uGBAQSAJ3bsDW3Io2dbEsgE2i7c0HyPQA==",
      "public_key": "llgByGIvi77pfGaYhY3TEErW5xeuQKWL6dcmA3d7oqtIhiuisRjjRE3fsU5oqbrLXOsqGrFa7HC4lS4TJ+a3sA==",
      "hash": "822a5d01a9e47ab9bc3d0e4c5556be8063220f9a7f8df2960db422fbe6333259"
    },
    {
      "inputs": [],
      "outputs": [
        {
          "address": "b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d",
          "amount": 55
        }
      ],
      "timestamp": 1652742613642153100,
      "signature": null,
      "public_key": null,
      "hash": "6889cb550c4af6417e3657455c63bcd573efbe7264a3f7cd9053caaa414fd178"
    }
  ]
}
```
- `404`: if no block with that hash exists in our main chain.

#### Get next block: `GET /blocks/get-next?current-tip=<block-hash>`

parameters:
- `current-tip`: Our current tip hash, otherwise it will return the Genesis block (optional)

example:
`GET /blocks/get-next?current-tip=00000652676efb2ebcbde6aa2c1aa3212d4f06c3ee102638a5add0a64a5620a2`

response:
- `200`:
```
{
  "timestamp": 1652742896006113000,
  "prev": "00000652676efb2ebcbde6aa2c1aa3212d4f06c3ee102638a5add0a64a5620a2",
  "nonce": 176255,
  "hash": "0000094df9279b9a78169981a7e106b0279a683d5921115e5d8fe8163a7907ef",
  "transactions": [
    {
      "inputs": [
        {
          "transaction_id": "822a5d01a9e47ab9bc3d0e4c5556be8063220f9a7f8df2960db422fbe6333259",
          "vout": 1
        }
      ],
      "outputs": [
        {
          "address": "b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225",
          "amount": 10
        },
        {
          "address": "b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d",
          "amount": 25
        }
      ],
      "timestamp": 1652550310128397000,
      "signature": "03rL5N8jtb8uhzemIDOm3TzqtOPAvg2Q8Rno5QMtdBQvFWxfqxKw1G6R4nSjG3Q13FSgpgUWej0E6BysuaRAKg==",
      "public_key": "llgByGIvi77pfGaYhY3TEErW5xeuQKWL6dcmA3d7oqtIhiuisRjjRE3fsU5oqbrLXOsqGrFa7HC4lS4TJ+a3sA==",
      "hash": "9be176ca5649bfd393afd61c8a6bb09562d80095916e46f22afca2ce35df34dc"
    },
    {
      "inputs": [],
      "outputs": [
        {
          "address": "b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d",
          "amount": 50
        }
      ],
      "timestamp": 1652742896006126600,
      "signature": null,
      "public_key": null,
      "hash": "882ec656899843400c81f73fcf8c804c9951cae278b03d8e4b90b8b3e718ae3b"
    }
  ]
}
```
- `400`: if no block with that hash exists in our main chain
- `404`: if this is also our tip.

#### Receive block: `POST /blocks`

body: `Block`

example:
`POST /blocks`
```
{
  "timestamp": 1652742896006113000,
  "prev": "00000652676efb2ebcbde6aa2c1aa3212d4f06c3ee102638a5add0a64a5620a2",
  "nonce": 176255,
  "hash": "0000094df9279b9a78169981a7e106b0279a683d5921115e5d8fe8163a7907ef",
  "transactions": [
    {
      "inputs": [
        {
          "transaction_id": "822a5d01a9e47ab9bc3d0e4c5556be8063220f9a7f8df2960db422fbe6333259",
          "vout": 1
        }
      ],
      "outputs": [
        {
          "address": "b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225",
          "amount": 10
        },
        {
          "address": "b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d",
          "amount": 25
        }
      ],
      "timestamp": 1652550310128397000,
      "signature": "03rL5N8jtb8uhzemIDOm3TzqtOPAvg2Q8Rno5QMtdBQvFWxfqxKw1G6R4nSjG3Q13FSgpgUWej0E6BysuaRAKg==",
      "public_key": "llgByGIvi77pfGaYhY3TEErW5xeuQKWL6dcmA3d7oqtIhiuisRjjRE3fsU5oqbrLXOsqGrFa7HC4lS4TJ+a3sA==",
      "hash": "9be176ca5649bfd393afd61c8a6bb09562d80095916e46f22afca2ce35df34dc"
    },
    {
      "inputs": [],
      "outputs": [
        {
          "address": "b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d",
          "amount": 50
        }
      ],
      "timestamp": 1652742896006126600,
      "signature": null,
      "public_key": null,
      "hash": "882ec656899843400c81f73fcf8c804c9951cae278b03d8e4b90b8b3e718ae3b"
    }
  ]
}
```

response: `202`

### TRANSACTIONS

#### Get transaction: `GET /transactions/<transaction_id>`

example:
`GET /transactions/822a5d01a9e47ab9bc3d0e4c5556be8063220f9a7f8df2960db422fbe6333259`

response:
- `200`:
```
{
    "hash": "822a5d01a9e47ab9bc3d0e4c5556be8063220f9a7f8df2960db422fbe6333259",
    "inputs": [
        {
            "transaction_id": "d0d9da8e1c009d6c19854d7bc0bce911c4e94afb86b9cfbcf0ce7e8004bf19b8",
            "vout": 0
        }
    ],
    "outputs": [
        {
            "address": "b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225",
            "amount": 10
        },
        {
            "address": "b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d",
            "amount": 35
        }
    ],
    "public_key": "llgByGIvi77pfGaYhY3TEErW5xeuQKWL6dcmA3d7oqtIhiuisRjjRE3fsU5oqbrLXOsqGrFa7HC4lS4TJ+a3sA==",
    "signature": "cDf/+00aNMis90SJGYEDzAYbirT51ZXslGpUnd+jmCU/jGiBHRW+9uGBAQSAJ3bsDW3Io2dbEsgE2i7c0HyPQA==",
    "timestamp": 1652550310128397000
}
```

#### Receive transaction: `POST /transactions`

body: `Transaction`

example:
`POST /transactions`
```
{
    "hash": "9be176ca5649bfd393afd61c8a6bb09562d80095916e46f22afca2ce35df34dc",
    "inputs": [
        {
            "transaction_id": "822a5d01a9e47ab9bc3d0e4c5556be8063220f9a7f8df2960db422fbe6333259",
            "vout": 1
        }
    ],
    "outputs": [
        {
            "address": "b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225",
            "amount": 10
        },
        {
            "address": "b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d",
            "amount": 25
        }
    ],
    "public_key": "llgByGIvi77pfGaYhY3TEErW5xeuQKWL6dcmA3d7oqtIhiuisRjjRE3fsU5oqbrLXOsqGrFa7HC4lS4TJ+a3sA==",
    "signature": "wejDj5k/aBH7vB6DGc+Ci56kzy+iePU4cHmQ1/M+rRms0aEDgV6/cRcvJJD993Af3nh/wkhEZxzHMMOFhX0PRw==",
    "timestamp": 1652550310128397000
}
```

#### Sign transaction: `POST /transactions/sign?add-to-transaction-pool`

parameters:
- `add-to-transaction-pool`: Also add the transaction to the transaction pool (optional)

body:
```
{
    "key": private key for address, base64 encoded
    "transaction: Transaction (without signature or public_key fields)
}
```

example:
`POST /transactions/sign`
```
{
  "key": "34AltHOoDslK7979JJcGKEo+eMnDcyx3W3obymEw+3g=",
  "transaction": {
    "inputs": [
      {
        "transaction_id": "822a5d01a9e47ab9bc3d0e4c5556be8063220f9a7f8df2960db422fbe6333259",
        "vout": 1
      }
    ],
    "outputs": [
      {
        "address": "b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225",
        "amount": 10
      },
      {
        "address": "b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d",
        "amount": 25
      }
    ],
    "timestamp": 1652550310128397000
  }
}
```

response:
- `200`:
```
{
    "hash": "9be176ca5649bfd393afd61c8a6bb09562d80095916e46f22afca2ce35df34dc",
    "inputs": [
        {
            "transaction_id": "822a5d01a9e47ab9bc3d0e4c5556be8063220f9a7f8df2960db422fbe6333259",
            "vout": 1
        }
    ],
    "outputs": [
        {
            "address": "b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225",
            "amount": 10
        },
        {
            "address": "b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d",
            "amount": 25
        }
    ],
    "public_key": "llgByGIvi77pfGaYhY3TEErW5xeuQKWL6dcmA3d7oqtIhiuisRjjRE3fsU5oqbrLXOsqGrFa7HC4lS4TJ+a3sA==",
    "signature": "wejDj5k/aBH7vB6DGc+Ci56kzy+iePU4cHmQ1/M+rRms0aEDgV6/cRcvJJD993Af3nh/wkhEZxzHMMOFhX0PRw==",
    "timestamp": 1652550310128397000
}
```

## Control API

### MINING

#### Mine: `POST /mine`

Can be used to mine a block when no miner thread is running

example:
`POST /mine`

response:
- `200`:
```
{
  "timestamp": 1652742896006113000,
  "prev": "00000652676efb2ebcbde6aa2c1aa3212d4f06c3ee102638a5add0a64a5620a2",
  "nonce": 176255,
  "hash": "0000094df9279b9a78169981a7e106b0279a683d5921115e5d8fe8163a7907ef",
  "transactions": [
    {
      "inputs": [
        {
          "transaction_id": "822a5d01a9e47ab9bc3d0e4c5556be8063220f9a7f8df2960db422fbe6333259",
          "vout": 1
        }
      ],
      "outputs": [
        {
          "address": "b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225",
          "amount": 10
        },
        {
          "address": "b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d",
          "amount": 25
        }
      ],
      "timestamp": 1652550310128397000,
      "signature": "03rL5N8jtb8uhzemIDOm3TzqtOPAvg2Q8Rno5QMtdBQvFWxfqxKw1G6R4nSjG3Q13FSgpgUWej0E6BysuaRAKg==",
      "public_key": "llgByGIvi77pfGaYhY3TEErW5xeuQKWL6dcmA3d7oqtIhiuisRjjRE3fsU5oqbrLXOsqGrFa7HC4lS4TJ+a3sA==",
      "hash": "9be176ca5649bfd393afd61c8a6bb09562d80095916e46f22afca2ce35df34dc"
    },
    {
      "inputs": [],
      "outputs": [
        {
          "address": "b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d",
          "amount": 50
        }
      ],
      "timestamp": 1652742896006126600,
      "signature": null,
      "public_key": null,
      "hash": "882ec656899843400c81f73fcf8c804c9951cae278b03d8e4b90b8b3e718ae3b"
    }
  ]
}
```
- `409`: if a new block was received while mining

### PERSISTENCE

#### Save blockchain to file: `POST /persistence/save`

example:
`POST /persistence/save`
```
{
    "filename": "chain.json"
}
```

response: `200`

#### Load blockchain from file: `POST /persistence/load`

example:
`POST /persistence/save`
```
{
    "filename": "chain.json"
}
```

response: `200`

### SYNCHRONIZATION

#### Synchronize: `POST /synchronize`

Can be used to force resynchronization from peers after a call to `/persistence/load`

example:
`POST /resynchronize`
