// authMiddleware.js
const jwt = require('jsonwebtoken');
const { SECRET_KEY } = require('../config/config');

function verifyToken(req, res, next) {
    const token = req.cookies.token;
    if (!token) {
        return res.status(401).json({ message: 'NoToken', redirect: '/login' });
    }

    jwt.verify(token, 'your_secret_jwt_key', (err, decoded) => {
        if (err) {
            return res.status(401).json({ message: 'InvalidToken', redirect: '/login' });
        }
        req.user = decoded;
        next();
    });
}

module.exports = verifyToken;
