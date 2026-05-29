package com.example.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "users")
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "email", nullable = false, unique = true, length = 200)
    private String email;

    @Column(name = "name", length = 100)
    private String name;

    @Column(name = "age")
    private Integer age;

    @Column(name = "created_at")
    private LocalDateTime createdAt;
}
