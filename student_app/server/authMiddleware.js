// authMiddleware.js
const jwt = require('jsonwebtoken');
const config = require('../config/config');
const SECRET_KEY = config.secret_key.key;

function verifyToken(req, res, next) {
    const token = req.cookies.token;
    if (!token) {
        res.redirect('/login?message=InvalidToken');
    }

    jwt.verify(token.replace('Bearer ', ''), config.secret_key.key, (err, decoded) => {
        if (err) {
            return res.status(500).send({ auth: false, message: 'Failed to authenticate token.' });
        }

        // Check if the token contains an 'exp' field
        if (!decoded.exp) {
            return res.status(500).send({ auth: false, message: 'Token does not have an expiration date.' });
        }

        // If everything is good, save to request for use in other routes
        req.user = decoded;
        next();
    });
}

module.exports = verifyToken;
