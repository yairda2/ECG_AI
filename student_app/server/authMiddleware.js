// authMiddleware.js

const jwt = require('jsonwebtoken');

function checkToken(req, res, next) {
    const token = req.cookies.token;
    if (!token) {
        return res.status(401).json({ message: 'NoToken' });
    }

    jwt.verify(token, 'your_secret_jwt_key', (err, decoded) => {
        if (err) {
            return res.status(401).json({ message: 'InvalidToken' });
        }
        req.user = decoded;
        next();
    });
}

module.exports = checkToken;
