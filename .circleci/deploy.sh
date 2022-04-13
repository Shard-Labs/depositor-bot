ssh -p $SSH_PORT -T $SSH_USER@$SSH_HOST <<EOA

ssh -T $SSH_NESTED_HOST <<EOB

cd /srv/depositor-bot

git fetch
git checkout $CIRCLE_BRANCH
git pull

echo "INFURA_API_KEY=$INFURA_API_KEY" > .env
echo "INFURA_API_KEY=$INFURA_API_KEY"

EOB

EOA