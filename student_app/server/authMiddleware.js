// authMiddleware.js
const jwt = require('jsonwebtoken');
const config = require('../config/config');
const SECRET_KEY = config.secret_key.key;

function verifyToken(req, res, next) {
    const token = req.cookies.token;
    if (!token) {
        return res.status(401).json({ message: 'NoToken', redirect: '/login' });
    }

    jwt.verify(token, SECRET_KEY, (err, decoded) => {
        if (err) {
            return res.status(401).json({ message: 'InvalidToken', redirect: '/login' });
        }
        req.user = decoded;
        // Add here check if the id exists in the database
        next();
    });
}

module.exports = verifyToken;
