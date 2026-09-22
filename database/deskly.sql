-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Tempo de geração: 22/09/2026 às 02:38
-- Versão do servidor: 10.4.32-MariaDB
-- Versão do PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Banco de dados: `deskly`
--
CREATE DATABASE IF NOT EXISTS `deskly` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `deskly`;

-- --------------------------------------------------------

--
-- Estrutura para tabela `chamado`
--

CREATE TABLE `chamado` (
  `IdChamado` int(10) NOT NULL,
  `IdEmpresa` int(10) NOT NULL,
  `IdTecnico` int(10) NOT NULL,
  `IdFuncionario` int(10) NOT NULL,
  `IdPrioridade` int(10) NOT NULL,
  `Descricao` varchar(500) NOT NULL,
  `Previsao` varchar(25) NOT NULL,
  `DataHoraAbertura` datetime NOT NULL,
  `TempoGasto` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `empresa`
--

CREATE TABLE `empresa` (
  `IdEmpresa` int(10) NOT NULL,
  `RazaoSocial` varchar(255) NOT NULL,
  `Cnpj` varchar(14) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `equipetecnica`
--

CREATE TABLE `equipetecnica` (
  `IdEquipe` int(10) NOT NULL,
  `IdEmpresa` int(10) NOT NULL,
  `NomeEquipe` varchar(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `funcionariopadrao`
--

CREATE TABLE `funcionariopadrao` (
  `IdFuncionario` int(10) NOT NULL,
  `IdUsuario` int(10) NOT NULL,
  `IdSetor` int(10) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `funcionariotecncio`
--

CREATE TABLE `funcionariotecncio` (
  `IdTecnico` int(10) NOT NULL,
  `IdUsuario` int(10) NOT NULL,
  `IdEquipe` int(10) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `prioridade`
--

CREATE TABLE `prioridade` (
  `IdPrioridade` int(10) NOT NULL,
  `DescricaoPrioridade` varchar(30) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `prioridade`
--

INSERT INTO `prioridade` (`IdPrioridade`, `DescricaoPrioridade`) VALUES
(1, 'Crítica'),
(2, 'Alta'),
(3, 'Média'),
(4, 'Baixa');

-- --------------------------------------------------------

--
-- Estrutura para tabela `setor`
--

CREATE TABLE `setor` (
  `IdSetor` int(10) NOT NULL,
  `IdEmpresa` int(10) NOT NULL,
  `NomeSetor` varchar(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `usuario`
--

CREATE TABLE `usuario` (
  `IdUsuario` int(10) NOT NULL,
  `IdEmpresa` int(10) NOT NULL,
  `NomeUsuario` varchar(255) NOT NULL,
  `SenhaHash` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Índices para tabelas despejadas
--

--
-- Índices de tabela `chamado`
--
ALTER TABLE `chamado`
  ADD PRIMARY KEY (`IdChamado`),
  ADD KEY `IdEmpresa` (`IdEmpresa`),
  ADD KEY `IdTecnico` (`IdTecnico`),
  ADD KEY `IdFuncionario` (`IdFuncionario`),
  ADD KEY `IdPrioridade` (`IdPrioridade`);

--
-- Índices de tabela `empresa`
--
ALTER TABLE `empresa`
  ADD PRIMARY KEY (`IdEmpresa`);

--
-- Índices de tabela `equipetecnica`
--
ALTER TABLE `equipetecnica`
  ADD PRIMARY KEY (`IdEquipe`),
  ADD KEY `IdEmpresa` (`IdEmpresa`);

--
-- Índices de tabela `funcionariopadrao`
--
ALTER TABLE `funcionariopadrao`
  ADD PRIMARY KEY (`IdFuncionario`),
  ADD KEY `IdUsuario` (`IdUsuario`),
  ADD KEY `IdSetor` (`IdSetor`);

--
-- Índices de tabela `funcionariotecncio`
--
ALTER TABLE `funcionariotecncio`
  ADD PRIMARY KEY (`IdTecnico`),
  ADD KEY `IdUsuario` (`IdUsuario`),
  ADD KEY `IdEquipe` (`IdEquipe`);

--
-- Índices de tabela `prioridade`
--
ALTER TABLE `prioridade`
  ADD PRIMARY KEY (`IdPrioridade`);

--
-- Índices de tabela `setor`
--
ALTER TABLE `setor`
  ADD PRIMARY KEY (`IdSetor`),
  ADD KEY `IdEmpresa` (`IdEmpresa`);

--
-- Índices de tabela `usuario`
--
ALTER TABLE `usuario`
  ADD PRIMARY KEY (`IdUsuario`),
  ADD KEY `IdEmpresa` (`IdEmpresa`);

--
-- AUTO_INCREMENT para tabelas despejadas
--

--
-- AUTO_INCREMENT de tabela `chamado`
--
ALTER TABLE `chamado`
  MODIFY `IdChamado` int(10) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `empresa`
--
ALTER TABLE `empresa`
  MODIFY `IdEmpresa` int(10) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `equipetecnica`
--
ALTER TABLE `equipetecnica`
  MODIFY `IdEquipe` int(10) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `funcionariopadrao`
--
ALTER TABLE `funcionariopadrao`
  MODIFY `IdFuncionario` int(10) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `funcionariotecncio`
--
ALTER TABLE `funcionariotecncio`
  MODIFY `IdTecnico` int(10) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `prioridade`
--
ALTER TABLE `prioridade`
  MODIFY `IdPrioridade` int(10) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT de tabela `setor`
--
ALTER TABLE `setor`
  MODIFY `IdSetor` int(10) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `usuario`
--
ALTER TABLE `usuario`
  MODIFY `IdUsuario` int(10) NOT NULL AUTO_INCREMENT;

--
-- Restrições para tabelas despejadas
--

--
-- Restrições para tabelas `chamado`
--
ALTER TABLE `chamado`
  ADD CONSTRAINT `chamado_ibfk_1` FOREIGN KEY (`IdEmpresa`) REFERENCES `empresa` (`IdEmpresa`),
  ADD CONSTRAINT `chamado_ibfk_2` FOREIGN KEY (`IdTecnico`) REFERENCES `funcionariotecncio` (`IdTecnico`),
  ADD CONSTRAINT `chamado_ibfk_3` FOREIGN KEY (`IdFuncionario`) REFERENCES `funcionariopadrao` (`IdFuncionario`),
  ADD CONSTRAINT `chamado_ibfk_4` FOREIGN KEY (`IdPrioridade`) REFERENCES `prioridade` (`IdPrioridade`);

--
-- Restrições para tabelas `equipetecnica`
--
ALTER TABLE `equipetecnica`
  ADD CONSTRAINT `equipetecnica_ibfk_1` FOREIGN KEY (`IdEmpresa`) REFERENCES `empresa` (`IdEmpresa`);

--
-- Restrições para tabelas `funcionariopadrao`
--
ALTER TABLE `funcionariopadrao`
  ADD CONSTRAINT `funcionariopadrao_ibfk_1` FOREIGN KEY (`IdUsuario`) REFERENCES `usuario` (`IdUsuario`),
  ADD CONSTRAINT `funcionariopadrao_ibfk_2` FOREIGN KEY (`IdSetor`) REFERENCES `setor` (`IdSetor`);

--
-- Restrições para tabelas `funcionariotecncio`
--
ALTER TABLE `funcionariotecncio`
  ADD CONSTRAINT `funcionariotecncio_ibfk_1` FOREIGN KEY (`IdUsuario`) REFERENCES `usuario` (`IdUsuario`),
  ADD CONSTRAINT `funcionariotecncio_ibfk_2` FOREIGN KEY (`IdEquipe`) REFERENCES `equipetecnica` (`IdEquipe`);

--
-- Restrições para tabelas `setor`
--
ALTER TABLE `setor`
  ADD CONSTRAINT `setor_ibfk_1` FOREIGN KEY (`IdEmpresa`) REFERENCES `empresa` (`IdEmpresa`);

--
-- Restrições para tabelas `usuario`
--
ALTER TABLE `usuario`
  ADD CONSTRAINT `usuario_ibfk_1` FOREIGN KEY (`IdEmpresa`) REFERENCES `empresa` (`IdEmpresa`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
