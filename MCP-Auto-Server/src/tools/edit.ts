import { readFile, writeFile, readFileInternal, validatePath } from './filesystem.js';
import fs from 'fs/promises';
import { ServerResult } from '../types.js';
import { EditBlockArgsSchema } from "./schemas.js";
import path from 'path';
import { detectLineEnding, normalizeLineEndings } from '../utils/lineEndingHandler.js';
import { configManager } from '../config-manager.js';

interface SearchReplace {
    search: string;
    replace: string;
}

interface FuzzyMatch {
    start: number;
    end: number;
    value: string;
    distance: number;
    similarity: number;
}

/**
 * Threshold for fuzzy matching - similarity must be at least this value to be considered
 * (0-1 scale where 1 is perfect match and 0 is completely different)
 */
const FUZZY_THRESHOLD = 0.7;

/**
 * Extract character code data from diff
 * @param expected The string that was searched for
 * @param actual The string that was found
 * @returns Character code statistics
 */
function getCharacterCodeData(expected: string, actual: string): {
    report: string;
    uniqueCount: number;
    diffLength: number;
} {
    // Find common prefix and suffix
    let prefixLength = 0;
    const minLength = Math.min(expected.length, actual.length);

    // Determine common prefix length
    while (prefixLength < minLength &&
           expected[prefixLength] === actual[prefixLength]) {
        prefixLength++;
    }

    // Determine common suffix length
    let suffixLength = 0;
    while (suffixLength < minLength - prefixLength &&
           expected[expected.length - 1 - suffixLength] === actual[actual.length - 1 - suffixLength]) {
        suffixLength++;
    }
    
    // Extract the different parts
    const expectedDiff = expected.substring(prefixLength, expected.length - suffixLength);
    const actualDiff = actual.substring(prefixLength, actual.length - suffixLength);
    
    // Count unique character codes in the diff
    const characterCodes = new Map<number, number>();
    const fullDiff = expectedDiff + actualDiff;
    
    for (let i = 0; i < fullDiff.length; i++) {
        const charCode = fullDiff.charCodeAt(i);
        characterCodes.set(charCode, (characterCodes.get(charCode) || 0) + 1);
    }
    
    // Create character codes string report
    const charCodeReport: string[] = [];
    characterCodes.forEach((count, code) => {
        // Include character representation for better readability
        const char = String.fromCharCode(code);
        // Make special characters more readable
        const charDisplay = code < 32 || code > 126 ? `\\x${code.toString(16).padStart(2, '0')}` : char;
        charCodeReport.push(`${code}:${count}[${charDisplay}]`);
    });
    
    // Sort by character code for consistency
    charCodeReport.sort((a, b) => {
        const codeA = parseInt(a.split(':')[0]);
        const codeB = parseInt(b.split(':')[0]);
        return codeA - codeB;
    });
    
    return {
        report: charCodeReport.join(','),
        uniqueCount: characterCodes.size,
        diffLength: fullDiff.length
    };
}

export async function performSearchReplace(filePath: string, block: SearchReplace, expectedReplacements: number = 1): Promise<ServerResult> {
    // Get file extension for telemetry using path module
    const fileExtension = path.extname(filePath).toLowerCase();

    // Read file directly to preserve line endings - critical for edit operations
    const validPath = await validatePath(filePath);
    const content = await readFileInternal(validPath, 0, Number.MAX_SAFE_INTEGER);
    
    // Make sure content is a string
    if (typeof content !== 'string') {
        throw new Error('Wrong content for file ' + filePath);
    }
    
    // Get the line limit from configuration
    const config = await configManager.getConfig();
    const MAX_LINES = config.fileWriteLineLimit ?? 50; // Default to 50 if not set
    
    // Detect file's line ending style
    const fileLineEnding = detectLineEnding(content);
    
    // Normalize search string to match file's line endings
    const normalizedSearch = normalizeLineEndings(block.search, fileLineEnding);
    
    // First try exact match
    let tempContent = content;
    let count = 0;
    let pos = tempContent.indexOf(normalizedSearch);
    
    while (pos !== -1) {
        count++;
        pos = tempContent.indexOf(normalizedSearch, pos + 1);
    }
    
    // If exact match found and count matches expected replacements, proceed with exact replacement
    if (count > 0 && count === expectedReplacements) {
        // Replace all occurrences
        let newContent = content;
        
        // If we're only replacing one occurrence, replace it directly
        if (expectedReplacements === 1) {
            const searchIndex = newContent.indexOf(normalizedSearch);
            newContent = 
                newContent.substring(0, searchIndex) + 
                normalizeLineEndings(block.replace, fileLineEnding) + 
                newContent.substring(searchIndex + normalizedSearch.length);
        } else {
            // Replace all occurrences using split and join for multiple replacements
            newContent = newContent.split(normalizedSearch).join(normalizeLineEndings(block.replace, fileLineEnding));
        }
        
        // Check if search or replace text has too many lines
        const searchLines = block.search.split('\n').length;
        const replaceLines = block.replace.split('\n').length;
        const maxLines = Math.max(searchLines, replaceLines);
        let warningMessage = "";
        
        if (maxLines > MAX_LINES) {
            const problemText = searchLines > replaceLines ? 'search text' : 'replacement text';
            warningMessage = `\n\nWARNING: The ${problemText} has ${maxLines} lines (maximum: ${MAX_LINES}).
            
RECOMMENDATION: For large search/replace operations, consider breaking them into smaller chunks with fewer lines.`;
        }
        
        await writeFile(filePath, newContent);
        return {
            content: [{ 
                type: "text", 
                text: `Successfully applied ${expectedReplacements} edit${expectedReplacements > 1 ? 's' : ''} to ${filePath}${warningMessage}` 
            }],
        };
    }
    
    // If exact match found but count doesn't match expected, inform the user
    if (count > 0 && count !== expectedReplacements) {
        return {
            content: [{ 
                type: "text", 
                text: `Expected ${expectedReplacements} occurrences but found ${count} in ${filePath}. ` + 
            `Double check and make sure you understand all occurencies and if you want to replace all ${count} occurrences, set expected_replacements to ${count}. ` +
            `If there are many occurrancies and you want to change some of them and keep the rest. Do it one by one, by adding more lines around each occurrence.` +
`If you want to replace a specific occurrence, make your search string more unique by adding more lines around search string.`
            }],
        };
    }
    
    throw new Error("Unexpected error during search and replace operation.");
}

/**
 * Generates a character-level diff using standard {-removed-}{+added+} format
 * @param expected The string that was searched for
 * @param actual The string that was found
 * @returns A formatted string showing character-level differences
 */
function highlightDifferences(expected: string, actual: string): string {
    // Implementation of a simplified character-level diff
    
    // Find common prefix and suffix
    let prefixLength = 0;
    const minLength = Math.min(expected.length, actual.length);

    // Determine common prefix length
    while (prefixLength < minLength &&
           expected[prefixLength] === actual[prefixLength]) {
        prefixLength++;
    }

    // Determine common suffix length
    let suffixLength = 0;
    while (suffixLength < minLength - prefixLength &&
           expected[expected.length - 1 - suffixLength] === actual[actual.length - 1 - suffixLength]) {
        suffixLength++;
    }
    
    // Extract the common and different parts
    const commonPrefix = expected.substring(0, prefixLength);
    const commonSuffix = expected.substring(expected.length - suffixLength);

    const expectedDiff = expected.substring(prefixLength, expected.length - suffixLength);
    const actualDiff = actual.substring(prefixLength, actual.length - suffixLength);

    // Format the output as a character-level diff
    return `${commonPrefix}{-${expectedDiff}-}{+${actualDiff}+}${commonSuffix}`;
}

/**
 * Handle edit_block command with enhanced functionality
 * - Supports multiple replacements
 * - Validates expected replacements count
 * - Provides detailed error messages
 */
export async function handleEditBlock(args: unknown): Promise<ServerResult> {
    const parsed = EditBlockArgsSchema.parse(args);
    
    const searchReplace = {
        search: parsed.old_string,
        replace: parsed.new_string
    };

    return performSearchReplace(parsed.file_path, searchReplace, parsed.expected_replacements);
}