const jwt = require('jsonwebtoken');
const config = require('../config/config');
const url = require('url');

function verifyToken(req, res, next) {
    const token = req.cookies.token || (req.headers['authorization'] && req.headers['authorization'].replace('Bearer ', ''));

    if (!token) {
        const currentUrl = encodeURIComponent(req.originalUrl);
        return res.redirect(`/login?message=NoToken&redirectUrl=${currentUrl}`);
    }

    jwt.verify(token, config.secret_key.key, (err, decoded) => {
        if (err) {
            const currentUrl = encodeURIComponent(req.originalUrl);

            if (err.name === 'TokenExpiredError') {
                return res.redirect(`/login?message=TokenExpired&redirectUrl=${currentUrl}`);
            }

            return res.status(500).json({ auth: false, message: 'Failed to authenticate token.' });
        }

        if (!decoded.exp) {
            return res.status(500).json({ auth: false, message: 'Token does not have an expiration date.' });
        }

        req.user = decoded;
        next();
    });
}

module.exports = verifyToken;
