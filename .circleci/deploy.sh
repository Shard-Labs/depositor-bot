ssh -p $SSH_PORT -T $SSH_USER@$SSH_HOST <<EOA

ssh -T $SSH_NESTED_HOST <<EOB

cd /srv/depositor-bot

git fetch
git checkout $CIRCLE_BRANCH
git pull

echo "$MAX_GAS_FEE" > .env
echo "testing" >> .env
echo "$MAX_GAS_FEE"
cat .env

EOB

EOA