<?php

function auth_json_error(int $statusCode, string $message): void {
    http_response_code($statusCode);
    echo json_encode([
        'success' => false,
        'message' => $message
    ]);
    exit();
}

function auth_base64url_encode(string $data): string {
    return rtrim(strtr(base64_encode($data), '+/', '-_'), '=');
}

function auth_base64url_decode(string $data): string|false {
    $remainder = strlen($data) % 4;
    if ($remainder > 0) {
        $data .= str_repeat('=', 4 - $remainder);
    }
    return base64_decode(strtr($data, '-_', '+/'), true);
}

function auth_token_secret(): string {
    return getenv('APP_TOKEN_SECRET') ?: 'change-this-token-secret';
}

function create_auth_token(array $payload): string {
    $issuedAt = time();
    $payload['iat'] = $issuedAt;
    $payload['exp'] = $issuedAt + (7 * 24 * 60 * 60);

    $payloadPart = auth_base64url_encode(json_encode($payload));
    $signature = hash_hmac('sha256', $payloadPart, auth_token_secret(), true);
    $signaturePart = auth_base64url_encode($signature);

    return $payloadPart . '.' . $signaturePart;
}

function get_bearer_token(): ?string {
    $header = $_SERVER['HTTP_AUTHORIZATION'] ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? '';
    if ($header === '' && function_exists('getallheaders')) {
        $headers = getallheaders();
        $header = $headers['Authorization'] ?? $headers['authorization'] ?? '';
    }

    if (preg_match('/Bearer\s+(.+)/i', $header, $matches) === 1) {
        return trim($matches[1]);
    }

    return null;
}

function parse_auth_token(string $token): ?array {
    $parts = explode('.', $token);
    if (count($parts) !== 2) {
        return null;
    }

    [$payloadPart, $signaturePart] = $parts;
    $expectedRaw = hash_hmac('sha256', $payloadPart, auth_token_secret(), true);
    $providedRaw = auth_base64url_decode($signaturePart);
    if ($providedRaw === false || !hash_equals($expectedRaw, $providedRaw)) {
        return null;
    }

    $payloadJson = auth_base64url_decode($payloadPart);
    if ($payloadJson === false) {
        return null;
    }

    $payload = json_decode($payloadJson, true);
    if (!is_array($payload)) {
        return null;
    }

    if (!isset($payload['userId'], $payload['email'], $payload['role'], $payload['exp'])) {
        return null;
    }

    if ((int)$payload['exp'] < time()) {
        return null;
    }

    return $payload;
}

function require_auth(PDO $db): array {
    $token = get_bearer_token();
    if (!$token) {
        auth_json_error(401, 'Missing bearer token');
    }

    $payload = parse_auth_token($token);
    if (!$payload) {
        auth_json_error(401, 'Invalid or expired token');
    }

    $stmt = $db->prepare('SELECT id, email, role FROM users WHERE id = :id LIMIT 1');
    $stmt->execute([':id' => (int)$payload['userId']]);
    $user = $stmt->fetch(PDO::FETCH_ASSOC);

    if (!$user) {
        auth_json_error(401, 'User not found');
    }

    if (
        (int)$user['id'] !== (int)$payload['userId'] ||
        $user['email'] !== $payload['email'] ||
        $user['role'] !== $payload['role']
    ) {
        auth_json_error(401, 'Token no longer valid for this user');
    }

    return $user;
}

function require_roles(array $user, array $allowedRoles): void {
    if (!in_array($user['role'], $allowedRoles, true)) {
        auth_json_error(403, 'Forbidden');
    }
}

