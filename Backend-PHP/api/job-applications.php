<?php
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

header("Content-Type: application/json");

require_once __DIR__ . '/../config/database.php';

$job_id = $_GET['job_id'] ?? null;

if (!$job_id) {
    echo json_encode([
        "success" => false,
        "message" => "Job ID required"
    ]);
    exit();
}

try {
    $database = new Database();
    $db = $database->getConnection();

    function normalizePortfolioUrl($raw) {
        if (!is_string($raw)) {
            return null;
        }
        $url = trim($raw);
        if ($url === '') {
            return null;
        }
        if (stripos($url, 'www.') === 0) {
            $url = 'https://' . $url;
        } elseif (!preg_match('#^https?://#i', $url)) {
            $looksLikeDomain = preg_match('/^(?:[a-z0-9-]+\.)+[a-z]{2,}(?:[\/:?#].*)?$/i', $url) === 1;
            if ($looksLikeDomain && strpos($url, '@') === false) {
                $url = 'https://' . $url;
            }
        }
        if (!filter_var($url, FILTER_VALIDATE_URL)) {
            return null;
        }
        $parts = parse_url($url);
        $scheme = strtolower($parts['scheme'] ?? '');
        if (!in_array($scheme, ['http', 'https'], true)) {
            return null;
        }
        return $url;
    }

    function classifyPortfolioLink($url) {
        $normalized = normalizePortfolioUrl($url);
        if ($normalized === null) {
            return null;
        }

        $parts = parse_url($normalized);
        $host = strtolower($parts['host'] ?? '');
        $path = strtolower($parts['path'] ?? '');
        if (str_starts_with($host, 'www.')) {
            $host = substr($host, 4);
        }

        if (str_ends_with($host, 'linkedin.com')) {
            return ['label' => 'LinkedIn', 'url' => $normalized];
        }
        if (str_ends_with($host, 'github.com')) {
            return ['label' => 'GitHub', 'url' => $normalized];
        }

        $blockedCourseDomains = [
            'coursera.org', 'udemy.com', 'edx.org', 'classcentral.com',
            'skillshare.com', 'udacity.com', 'pluralsight.com', 'codecademy.com',
            'freecodecamp.org', 'geeksforgeeks.org', 'youtube.com', 'youtu.be'
        ];
        foreach ($blockedCourseDomains as $domain) {
            if ($host === $domain || str_ends_with($host, '.' . $domain)) {
                return null;
            }
        }

        $blockedPathTokens = ['/course', '/courses', '/learn', '/learning', '/tutorial', '/tutorials', '/certificate', '/certification', '/bootcamp'];
        foreach ($blockedPathTokens as $token) {
            if ($path !== '' && strpos($path, $token) !== false) {
                return null;
            }
        }

        $ext = pathinfo($path, PATHINFO_EXTENSION);
        $blocked = ['pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'csv', 'txt', 'zip', 'rar', '7z', 'jpg', 'jpeg', 'png', 'gif', 'webp'];
        if ($ext && in_array($ext, $blocked, true)) {
            return null;
        }

        return ['label' => 'Website', 'url' => $normalized];
    }

    function filterPortfolioLinks($links) {
        $filtered = [];
        $seen = [];
        foreach ($links as $link) {
            if (!is_array($link) || empty($link['url'])) {
                continue;
            }
            $classified = classifyPortfolioLink($link['url']);
            if ($classified === null) {
                continue;
            }
            $key = strtolower($classified['url']);
            if (isset($seen[$key])) {
                continue;
            }
            $seen[$key] = true;
            $filtered[] = $classified;
        }
        return $filtered;
    }

    function fetchPdfLinks($filename) {
        if (empty($filename)) {
            return [];
        }

        $payload = json_encode(['filename' => $filename]);
        $ch = curl_init("http://localhost:5001/extract-links");
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
        curl_setopt($ch, CURLOPT_TIMEOUT, 5);

        $response = curl_exec($ch);
        $error = curl_error($ch);
        curl_close($ch);

        if ($error || !$response) {
            return [];
        }

        $data = json_decode($response, true);
        if (!$data || empty($data['success'])) {
            return [];
        }

        return filterPortfolioLinks($data['links'] ?? []);
    }

    $query = "
    SELECT 
        a.*,
        NULLIF(TRIM(CONCAT(COALESCE(p.first_name, ''), ' ', COALESCE(p.last_name, ''))), '') AS candidate_name,
        u.email AS candidate_email,
        u.id AS candidate_id,
        r.resume_data AS resume_data
    FROM applications a
    JOIN users u ON a.candidate_id = u.id
    LEFT JOIN profiles p ON u.id = p.user_id
    LEFT JOIN resumes r ON u.id = r.user_id
    WHERE a.job_id = :job_id
    ORDER BY a.applied_at DESC
";

    $stmt = $db->prepare($query);
    $stmt->bindParam(':job_id', $job_id, PDO::PARAM_INT);
    $stmt->execute();

    $applications = $stmt->fetchAll(PDO::FETCH_ASSOC);

    foreach ($applications as &$app) {
        $links = [];
        if (!empty($app['resume_data'])) {
            $decoded = json_decode($app['resume_data'], true);
            if (json_last_error() === JSON_ERROR_NONE && is_array($decoded)) {
                $personalInfo = $decoded['personalInfo'] ?? [];
                $linkedIn = $personalInfo['linkedIn'] ?? '';
                $portfolio = $personalInfo['portfolio'] ?? '';
                $website = $personalInfo['website'] ?? '';

                $links = filterPortfolioLinks([
                    ['url' => $linkedIn],
                    ['url' => $portfolio],
                    ['url' => $website]
                ]);
            }
        }
        if (empty($links) && !empty($app['resume_filename'])) {
            $links = fetchPdfLinks($app['resume_filename']);
        }

        $app['portfolio_links'] = $links;
        unset($app['resume_data']);
    }
    unset($app);

    echo json_encode([
        "success" => true,
        "applications" => $applications
    ]);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        "success" => false,
        "message" => "Failed to fetch job applications"
    ]);
}
