package com.example.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;

@Entity
@Table(name = "users")
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // renamed column: email -> email_address; also still unique
    @Column(name = "email_address", nullable = false, unique = true, length = 200)
    private String email;

    // made NOT NULL
    @NotNull
    @Column(name = "name", length = 100)
    private String name;

    // age dropped (field removed entirely)

    // new nullable column
    @Column(name = "phone", length = 20)
    private String phone;

    // new enum-like column (VARCHAR 50)
    @Column(name = "status", nullable = false, length = 50)
    private String status;

    // new numeric column
    @Column(name = "credit_limit")
    private BigDecimal creditLimit;
}
