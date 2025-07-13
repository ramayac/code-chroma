package org.example.utils;

import java.util.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * Utility class for data processing and validation
 * Provides common helper methods for string manipulation, date handling, and validation
 */
public class DataProcessor {
    
    private static final DateTimeFormatter DEFAULT_DATE_FORMAT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final int DEFAULT_MAX_LENGTH = 255;
    
    /**
     * Validates if a string is not null and not empty
     * @param str the string to validate
     * @return true if the string is valid, false otherwise
     */
    public static boolean isValidString(String str) {
        return str != null && !str.trim().isEmpty();
    }
    
    /**
     * Validates if a string meets length requirements
     * @param str the string to validate
     * @param minLength minimum required length
     * @param maxLength maximum allowed length
     * @return true if the string length is valid, false otherwise
     */
    public static boolean isValidLength(String str, int minLength, int maxLength) {
        if (str == null) return false;
        int length = str.length();
        return length >= minLength && length <= maxLength;
    }
    
    /**
     * Sanitizes a string by removing HTML tags and special characters
     * @param input the input string to sanitize
     * @return the sanitized string
     */
    public static String sanitizeInput(String input) {
        if (input == null) return "";
        
        // Remove HTML tags
        String sanitized = input.replaceAll("<[^>]*>", "");
        
        // Remove special characters except alphanumeric, spaces, and basic punctuation
        sanitized = sanitized.replaceAll("[^a-zA-Z0-9\\s.,;:!?()-]", "");
        
        // Normalize whitespace
        sanitized = sanitized.replaceAll("\\s+", " ").trim();
        
        return sanitized;
    }
    
    /**
     * Formats a date to string using the default format
     * @param date the date to format
     * @return formatted date string
     */
    public static String formatDate(LocalDateTime date) {
        if (date == null) return "";
        return date.format(DEFAULT_DATE_FORMAT);
    }
    
    /**
     * Parses a date string using the default format
     * @param dateString the date string to parse
     * @return parsed LocalDateTime object
     * @throws Exception if the date string is invalid
     */
    public static LocalDateTime parseDate(String dateString) throws Exception {
        if (!isValidString(dateString)) {
            throw new IllegalArgumentException("Date string cannot be null or empty");
        }
        return LocalDateTime.parse(dateString, DEFAULT_DATE_FORMAT);
    }
    
    /**
     * Converts a list of strings to a comma-separated string
     * @param items the list of strings
     * @return comma-separated string
     */
    public static String joinStrings(List<String> items) {
        if (items == null || items.isEmpty()) return "";
        return String.join(", ", items);
    }
    
    /**
     * Splits a comma-separated string into a list of strings
     * @param input the comma-separated string
     * @return list of strings
     */
    public static List<String> splitString(String input) {
        if (!isValidString(input)) return new ArrayList<>();
        return Arrays.asList(input.split(",\\s*"));
    }
    
    /**
     * Generates a random alphanumeric string of specified length
     * @param length the length of the string to generate
     * @return random alphanumeric string
     */
    public static String generateRandomString(int length) {
        if (length <= 0) return "";
        
        String chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
        StringBuilder sb = new StringBuilder();
        Random random = new Random();
        
        for (int i = 0; i < length; i++) {
            sb.append(chars.charAt(random.nextInt(chars.length())));
        }
        
        return sb.toString();
    }
    
    /**
     * Calculates the percentage of one number relative to another
     * @param value the value to calculate percentage for
     * @param total the total value
     * @param precision the number of decimal places
     * @return percentage as a double
     */
    public static double calculatePercentage(double value, double total, int precision) {
        if (total == 0) return 0.0;
        double percentage = (value / total) * 100;
        return Math.round(percentage * Math.pow(10, precision)) / Math.pow(10, precision);
    }
    
    /**
     * Validates an email address format
     * @param email the email address to validate
     * @return true if the email format is valid, false otherwise
     */
    public static boolean isValidEmail(String email) {
        if (!isValidString(email)) return false;
        
        String emailRegex = "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$";
        return email.matches(emailRegex);
    }
    
    /**
     * Truncates a string to a specified length and adds ellipsis if needed
     * @param text the text to truncate
     * @param maxLength the maximum length
     * @return truncated string
     */
    public static String truncateString(String text, int maxLength) {
        if (text == null) return "";
        if (text.length() <= maxLength) return text;
        
        return text.substring(0, maxLength - 3) + "...";
    }
    
    /**
     * Capitalizes the first letter of each word in a string
     * @param text the text to capitalize
     * @return capitalized string
     */
    public static String capitalizeWords(String text) {
        if (!isValidString(text)) return "";
        
        StringBuilder result = new StringBuilder();
        boolean capitalizeNext = true;
        
        for (char c : text.toCharArray()) {
            if (Character.isWhitespace(c)) {
                capitalizeNext = true;
                result.append(c);
            } else if (capitalizeNext) {
                result.append(Character.toUpperCase(c));
                capitalizeNext = false;
            } else {
                result.append(Character.toLowerCase(c));
            }
        }
        
        return result.toString();
    }
    
    /**
     * Removes duplicate strings from a list while preserving order
     * @param items the list of strings
     * @return list with duplicates removed
     */
    public static List<String> removeDuplicates(List<String> items) {
        if (items == null) return new ArrayList<>();
        
        List<String> result = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        
        for (String item : items) {
            if (item != null && seen.add(item)) {
                result.add(item);
            }
        }
        
        return result;
    }
}
