# Jason here: idk how any of this crap works so 
# apparently you might have to change the version... gl

FROM node:16

# Optimize app for production
ENV NODE_ENV production

# Run app as node user instead of root
USER node

COPY --chown=node:node . /usr/src/app

# Create app directory
WORKDIR /usr/src/app

# Create media store
RUN mkdir /usr/src/app/media

# Install app dependencies
# A wildcard is used to ensure both package.json AND package-lock.json are copied
# where available (npm@5+)
COPY package*.json ./

# RUN npm install
# If you are building your code for production
RUN npm ci --only=production

# Bundle app source
COPY . .

EXPOSE 8080

CMD ["node", "app.js"]
