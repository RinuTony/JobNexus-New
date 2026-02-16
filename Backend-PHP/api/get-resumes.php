<?php
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json");
header("Access-Control-Allow-Methods: GET, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

$user_id = $_GET['user_id'] ?? null;

if (!$user_id) {
    echo json_encode([
        'success' => false,
        'message' => 'User ID required'
    ]);
    exit();
}

try {
    require_once __DIR__ . '/../config/database.php';
    
    $database = new Database();
    $db = $database->getConnection();
    
    if (!$db) {
        throw new Exception('Database connection failed');
    }
    
    // First, just check if table exists and has data
    $checkSql = "SELECT COUNT(*) as count FROM resumes WHERE user_id = :user_id";
    $checkStmt = $db->prepare($checkSql);
    $checkStmt->execute([':user_id' => $user_id]);
    $count = $checkStmt->fetch(PDO::FETCH_ASSOC);
    
    // Now get the actual data
    $sql = "SELECT 
                id,
                title,
                resume_data,
                template_id,
                created_at,
                updated_at
            FROM resumes 
            WHERE user_id = :user_id 
            ORDER BY created_at DESC";
    
    $stmt = $db->prepare($sql);
    $stmt->execute([':user_id' => $user_id]);
    
    $resumes = [];
    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
        $resumes[] = [
            'id' => (int)$row['id'],
            'title' => $row['title'] ?? 'My Resume',
            'resume_data' => json_decode($row['resume_data'], true),
            'template_id' => (int)$row['template_id'],
            'created_at' => $row['created_at'],
            'updated_at' => $row['updated_at']
        ];
    }
    
    echo json_encode([
        'success' => true,
        'count' => $count['count'],
        'resumes' => $resumes
    ]);
    
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'message' => 'Database error',
        'error' => $e->getMessage(),
        'code' => $e->getCode()
    ]);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'message' => 'Failed to fetch resumes',
        'error' => $e->getMessage()
    ]);
}
?>
