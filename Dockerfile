# Use arm32v7 to run on Raspberry Pi 3
FROM arm32v7/node:16.13.0-slim

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

#RUN npm install
# If you are building your code for production
RUN npm ci --only=production

# Bundle app source
COPY . .

EXPOSE 8080
#CMD ["node", "app.js"]
CMD ["node", "app.js"]
