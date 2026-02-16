<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);

header("Access-Control-Allow-Origin: http://localhost:3000");
header("Access-Control-Allow-Headers: Content-Type");
header("Content-Type: application/json");

$input = json_decode(file_get_contents("php://input"), true);

if (!$input || !isset($input['jobDescription'])) {
    echo json_encode(["success" => false, "message" => "Job description required"]);
    exit();
}

$jobDesc = $input['jobDescription'];

$apiKey = "AIzaSyAJVMtGDolI89wXOTudZ99U11jwoadFLhs";

$url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=$apiKey";

$payload = [
    "contents" => [
        [
            "parts" => [
                ["text" => "Rewrite this job description professionally:\n\n$jobDesc"]
            ]
        ]
    ]
];

$ch = curl_init($url);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, ["Content-Type: application/json"]);
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload));
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);

if ($response === false) {
    echo json_encode(["success" => false, "message" => curl_error($ch)]);
    exit();
}

curl_close($ch);

$data = json_decode($response, true);

if (!isset($data['candidates'][0]['content']['parts'][0]['text'])) {
    echo json_encode(["success" => false, "message" => "AI response invalid", "raw" => $data]);
    exit();
}

echo json_encode([
    "success" => true,
    "enhancedJD" => $data['candidates'][0]['content']['parts'][0]['text']
]);
