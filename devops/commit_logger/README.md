### Commit Logger

#### Requirements
(Assuming Python3 already installed)
`python3 -m pip install requests`
`python3 -m pip install flask`

#### Run commands
Using a Tmux session, run the logger:
```
pushd ./commit
python3 commit_logger.py --endpoints https://api.s0.os.hmny.io,https://api.s1.os.hmny.io,https://api.s2.os.hmny.io,https://api.s3.os.hmny.io
popd
```
Split into 2 panes & run the flask server:
```
export FLASK_APP=logger
python3 -m flask run -p 5010
```

#### Output
```
./commit/data/commit.json
./commit/data/commit_*.log
```
