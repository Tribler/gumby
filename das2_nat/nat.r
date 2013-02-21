library(ggplot2)
library(reshape)

r <- read.table("request.data", header=TRUE, row.names=1)
s <- read.table("success.data", header=TRUE, row.names=1)

colnames(r) <- 1:length(colnames(r))
colnames(s) <- colnames(r)

#resetting labels
colnames(r) <- 1:length(colnames(r))
colnames(s) <- 1:length(colnames(s))

rownames(r) <- colnames(r)
rownames(s) <- rownames(r)

sr <- s/r

r$From <- 1:length(rownames(r))
sr$From <- 1:length(rownames(sr))

rm <- melt(r, id.vars = "From")
srm <- melt(sr, id.vars = "From")

colnames(rm) <- c('From', 'To', 'Requests')
colnames(srm) <- c('From', 'To', 'Successrate')

d <- merge(rm, srm, sort=FALSE)
d <- na.omit(d)
midpoint <- 0.6

p <- ggplot(d, aes(x=To, y=From)) + theme_bw() + geom_point(aes(size=Requests, color=Successrate))
p <- p + scale_color_gradient2(low='red',mid="yellow", high="darkgreen", midpoint = midpoint)
p <- p + scale_y_continuous(breaks=seq(1,length(colnames(r)),1))
p <- p + labs(x = "Node Receiving", y = "Node Requesting") + opts(axis.text.x = theme_text(hjust = 0, colour = "grey50"), axis.text.y = theme_text(colour = "grey50"))
p

ggsave(file="nat.png", width=8, height=6, dpi=100)