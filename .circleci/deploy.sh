ssh -p $SSH_PORT -T $SSH_USER@$SSH_HOST <<EOA

ssh -T $SSH_NESTED_HOST <<EOB

cd /srv/depositor-bot

git fetch
git checkout $CIRCLE_BRANCH
git pull

echo "$WEB3_INFURA_PROJECT_ID" | base64 --decode > .env
echo "$MAX_GAS_FEE" | base64 --decode >> .env

EOB

EOA